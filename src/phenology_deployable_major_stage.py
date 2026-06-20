#!/usr/bin/env python3
"""Deployable major-stage calibration for the GrapeMaster phenology module.

The goal is operational crop-stage context, not fine-scale BBCH event dating.
The model predicts broad major stages from daily thermal accumulation, supports
cultivar-specific threshold tables and offsets, and simulates one user-confirmed
stage correction per crop season.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHENO_DIR = ROOT / "model_moudle" / "grape_bbch" / "standalone_phenology"
sys.path.insert(0, str(PHENO_DIR))

from evaluation import build_weather_inputs, scenario_key  # noqa: E402
from io_utils import SCENARIO_COLUMNS  # noqa: E402
from phenology_model import ThermalParams, get_thresholds, load_parameter_table, wang_engel  # noqa: E402


VARIETY_MAP = {
    "wk": {"variety": "温克", "maturation": "晚"},
    "JF": {"variety": "巨峰", "maturation": "中"},
    "MPT": {"variety": "毛葡萄野酿2号", "maturation": "晚"},
}

STAGE_ORDER = ["00", "10", "50", "60", "70", "80", "90"]
STAGE_RANK = {stage: i for i, stage in enumerate(STAGE_ORDER)}
STAGE_LABELS = {
    "00": "Budburst or early shoot emergence",
    "10": "Leaf development",
    "50": "Inflorescence emergence",
    "60": "Flowering",
    "70": "Berry development",
    "80": "Ripening",
    "90": "Post-harvest or senescence",
}

CULTIVAR_SEARCH_CONFIG = {
    "JF": {"offset_limit": 180.0, "offset_step": 10.0, "threshold_step": 10.0, "prior_weight": 2.0},
    "MPT": {"offset_limit": 180.0, "offset_step": 10.0, "threshold_step": 10.0, "prior_weight": 2.0},
    "wk": {"offset_limit": 300.0, "offset_step": 10.0, "threshold_step": 20.0, "prior_weight": 6.0},
}
EMPIRICAL_CULTIVAR_OFFSETS = {
    # 温克 uses a complete empirical boundary table below, so no additional
    # global offset is applied.
    "wk": 0.0,
}
EMPIRICAL_CULTIVAR_BOUNDARIES = {
    # Derived from the only 温克 site-year. Boundaries up to berry development
    # bracket the observed records; later boundaries are conservative carry-
    # forward values because no 温克 ripening or post-harvest observations are
    # available in the current calibration set.
    "wk": {"00": 0.0, "10": 10.0, "50": 80.0, "60": 180.0, "70": 240.0, "80": 520.0, "90": 1960.0},
}
TRANSITION_MARGIN_GDD = 100.0


@dataclass(frozen=True)
class BiofixRule:
    name: str
    tmean_threshold: float | None
    run_days: int | None


@dataclass(frozen=True)
class MajorStageModel:
    model: str
    biofix_rule: BiofixRule
    shared_boundaries: dict[str, float]
    cultivar_boundaries: dict[str, dict[str, float]]
    cultivar_offsets: dict[str, float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deployable major-stage phenology calibration.")
    parser.add_argument("--input", type=Path, default=PHENO_DIR / "data" / "growth_stage_data.xlsx")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "results" / "phenology_deployable_major_stage")
    parser.add_argument("--cache-dir", type=Path, default=ROOT / "results" / "phenology" / "weather_cache")
    parser.add_argument("--n-folds", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--min-cultivar-events", type=int, default=6)
    parser.add_argument("--min-cultivar-stages", type=int, default=3)
    return parser.parse_args()


def major_stage(bbch: str | int | float | None) -> str | None:
    if bbch is None or pd.isna(bbch):
        return None
    value = int(float(bbch))
    if value < 10:
        return "00"
    if 10 <= value <= 19:
        return "10"
    if 50 <= value <= 59:
        return "50"
    if 60 <= value <= 69:
        return "60"
    if 70 <= value <= 79:
        return "70"
    if 80 <= value <= 89:
        return "80"
    if 90 <= value <= 99:
        return "90"
    return None


def scenario_records(events: pd.DataFrame) -> list[dict]:
    return events[SCENARIO_COLUMNS].drop_duplicates().to_dict(orient="records")


def load_observations(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path)
    raw["date"] = pd.to_datetime(raw["date"])
    raw["year"] = raw["date"].dt.year.astype(int)
    observed = raw.dropna(subset=["growth_stage"]).copy()
    observed["BBCH_Principal"] = observed["growth_stage"].astype(int).astype(str).str.zfill(2)
    observed["major_stage"] = observed["BBCH_Principal"].map(major_stage)
    observed = observed.dropna(subset=["major_stage"]).copy()

    rows = []
    for _, row in observed.iterrows():
        code = str(row["variety"])
        mapped = VARIETY_MAP[code]
        rows.append(
            {
                "site_id": row["site"],
                "year": int(row["year"]),
                "province": "GuangXi",
                "variety": mapped["variety"],
                "source_variety_code": code,
                "maturation": mapped["maturation"],
                "lat": float(row["lat"]),
                "lon": float(row["lon"]),
                "BBCH_Principal": row["BBCH_Principal"],
                "major_stage": row["major_stage"],
                "major_stage_rank": STAGE_RANK[row["major_stage"]],
                "observed_date": row["date"].strftime("%Y-%m-%d"),
            }
        )
    return pd.DataFrame(rows).sort_values(SCENARIO_COLUMNS + ["observed_date"]).reset_index(drop=True)


def build_weather_inputs_for_events(events: pd.DataFrame, cache_dir: Path) -> dict:
    obs = events[SCENARIO_COLUMNS + ["BBCH_Principal", "observed_date"]].copy()
    return build_weather_inputs(obs, cache_dir)


def biofix_candidates() -> list[BiofixRule]:
    rules = [BiofixRule("jan1", None, None)]
    for threshold in [8.0, 10.0, 12.0]:
        for run_days in [3, 5, 7]:
            rules.append(BiofixRule(f"tmean_ge_{threshold:g}_run_{run_days}d", threshold, run_days))
    return rules


def daily_gdd(weather_rows: list[dict], rule: BiofixRule) -> pd.DataFrame:
    df = pd.DataFrame(weather_rows).copy()
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    df["date_dt"] = pd.to_datetime(df["Date"])
    df["temperature_2m_mean"] = pd.to_numeric(df["temperature_2m_mean"], errors="coerce").ffill()
    response = df["temperature_2m_mean"].apply(lambda x: wang_engel(float(x), ThermalParams()))

    biofix_date = df["date_dt"].min()
    active = pd.Series(True, index=df.index)
    if rule.tmean_threshold is not None and rule.run_days is not None:
        warm = df["temperature_2m_mean"] >= float(rule.tmean_threshold)
        run = warm.astype(int).groupby((~warm).cumsum()).cumsum()
        hit = df[run >= int(rule.run_days)]
        if not hit.empty:
            biofix_date = pd.to_datetime(hit.iloc[0]["date_dt"])
        active = df["date_dt"] >= biofix_date

    df["biofix_date"] = biofix_date.strftime("%Y-%m-%d")
    df["GDD"] = np.where(active, response, 0.0)
    df["GDDCUSUM"] = df["GDD"].cumsum()
    return df[["Date", "biofix_date", "GDDCUSUM"]]


def attach_gdd(events: pd.DataFrame, weather_inputs: dict, rule: BiofixRule) -> pd.DataFrame:
    frames = []
    for scenario in scenario_records(events):
        key = scenario_key(scenario)
        gdd = daily_gdd(weather_inputs[key], rule)
        sub = events.copy()
        for column, value in scenario.items():
            sub = sub[sub[column] == value]
        merged = sub.merge(gdd, left_on="observed_date", right_on="Date", how="left").drop(columns=["Date"])
        frames.append(merged)
    return pd.concat(frames, ignore_index=True)


def platform_major_prior(events: pd.DataFrame, parameter_table: dict) -> dict[str, float]:
    values: dict[str, list[float]] = {stage: [] for stage in STAGE_ORDER}
    values["00"].append(0.0)
    for scenario in scenario_records(events):
        thresholds = get_thresholds(
            scenario["province"],
            scenario["variety"],
            scenario["maturation"],
            parameter_table=parameter_table,
        )
        thresholds = thresholds.assign(major=thresholds["GS"].map(major_stage)).dropna(subset=["major"])
        for stage, group in thresholds.groupby("major"):
            values[stage].append(float(group["GDD"].min()))
    prior = {}
    last = 0.0
    for stage in STAGE_ORDER:
        candidates = values.get(stage) or []
        value = float(np.median(candidates)) if candidates else last + 100.0
        value = max(value, last + (0.0 if stage == "00" else 20.0))
        prior[stage] = value
        last = value
    return prior


def round_to_step(value: float, step: float) -> float:
    return float(round(value / step) * step)


def calibrate_boundaries(observed: pd.DataFrame, prior: dict[str, float], step: float, prior_weight: float) -> dict[str, float]:
    observed = observed.dropna(subset=["GDDCUSUM", "major_stage_rank"]).copy()
    targets: dict[str, float] = {"00": 0.0}
    weights: dict[str, float] = {"00": prior_weight}
    ranks = observed["major_stage_rank"].astype(int)
    gdd = observed["GDDCUSUM"].astype(float)

    for stage in STAGE_ORDER[1:]:
        rank = STAGE_RANK[stage]
        lower = observed[ranks < rank]
        upper = observed[ranks >= rank]
        if lower.empty or upper.empty:
            targets[stage] = prior[stage]
            weights[stage] = prior_weight
            continue
        lo = max(0.0, float(gdd.min()) - 50.0)
        hi = float(gdd.max()) + 50.0
        grid = np.arange(round_to_step(lo, step), round_to_step(hi, step) + step, step)
        best_threshold = prior[stage]
        best_score = math.inf
        for threshold in grid:
            score = int((lower["GDDCUSUM"] >= threshold).sum()) + int((upper["GDDCUSUM"] < threshold).sum())
            score += 0.002 * abs(float(threshold) - prior[stage])
            if score < best_score:
                best_score = score
                best_threshold = float(threshold)
        local_weight = min(len(lower), len(upper))
        targets[stage] = (local_weight * best_threshold + prior_weight * prior[stage]) / (local_weight + prior_weight)
        weights[stage] = local_weight + prior_weight

    out = {}
    last = 0.0
    for stage in STAGE_ORDER:
        value = round_to_step(targets[stage], step)
        if stage == "00":
            value = 0.0
        else:
            value = max(value, last + step)
        out[stage] = float(value)
        last = out[stage]
    return refine_boundaries(observed, out, prior, step)


def boundary_score(observed: pd.DataFrame, boundaries: dict[str, float], prior: dict[str, float]) -> float:
    if observed.empty:
        return math.inf
    preds = observed["GDDCUSUM"].apply(lambda x: predict_major_stage(float(x), boundaries, 0.0))
    pred_rank = preds.map(STAGE_RANK).to_numpy(dtype=int)
    obs_rank = observed["major_stage_rank"].to_numpy(dtype=int)
    distance = np.abs(pred_rank - obs_rank)
    severe = distance > 1
    prior_penalty = sum(abs(boundaries[s] - prior[s]) for s in STAGE_ORDER[1:]) / 10000.0
    return float(np.mean(2.0 * (distance > 0) + distance + 2.0 * severe) + prior_penalty)


def refine_boundaries(
    observed: pd.DataFrame,
    initial: dict[str, float],
    prior: dict[str, float],
    step: float,
    passes: int = 4,
) -> dict[str, float]:
    observed = observed.dropna(subset=["GDDCUSUM", "major_stage_rank"]).copy()
    if observed.empty:
        return initial
    best = dict(initial)
    min_gdd = max(0.0, float(observed["GDDCUSUM"].min()) - 50.0)
    max_gdd = float(observed["GDDCUSUM"].max()) + 50.0
    grid = np.arange(round_to_step(min_gdd, step), round_to_step(max_gdd, step) + step, step)

    for _ in range(passes):
        changed = False
        for i, stage in enumerate(STAGE_ORDER[1:], start=1):
            lower_bound = best[STAGE_ORDER[i - 1]] + step
            upper_bound = best[STAGE_ORDER[i + 1]] - step if i + 1 < len(STAGE_ORDER) else max_gdd
            candidates = [float(v) for v in grid if lower_bound <= v <= upper_bound]
            if not candidates:
                continue
            current_score = boundary_score(observed, best, prior)
            local_best = best[stage]
            local_score = current_score
            for candidate in candidates:
                trial = dict(best)
                trial[stage] = candidate
                score = boundary_score(observed, trial, prior)
                if score < local_score:
                    local_score = score
                    local_best = candidate
            if local_best != best[stage]:
                best[stage] = local_best
                changed = True
        if not changed:
            break
    return best


def predict_major_stage(gdd_value: float, boundaries: dict[str, float], offset: float = 0.0) -> str:
    adjusted = float(gdd_value) - float(offset)
    current = "00"
    for stage in STAGE_ORDER:
        if adjusted >= boundaries[stage]:
            current = stage
        else:
            break
    return current


def display_stage_prediction(gdd_value: float, boundaries: dict[str, float], offset: float = 0.0) -> tuple[str, str, bool]:
    adjusted = float(gdd_value) - float(offset)
    point_stage = predict_major_stage(float(gdd_value), boundaries, offset)
    best_boundary = None
    best_distance = math.inf
    best_pair = None
    for idx, upper_stage in enumerate(STAGE_ORDER[1:], start=1):
        distance = abs(adjusted - boundaries[upper_stage])
        if distance < best_distance:
            best_distance = distance
            best_boundary = upper_stage
            best_pair = (STAGE_ORDER[idx - 1], upper_stage)
    if best_boundary is not None and best_distance <= TRANSITION_MARGIN_GDD and best_pair is not None:
        return point_stage, f"{best_pair[0]}-{best_pair[1]}", True
    return point_stage, point_stage, False


def within_stage_progress(gdd_value: float, boundaries: dict[str, float], stage: str, offset: float = 0.0) -> float | None:
    idx = STAGE_RANK[stage]
    if idx + 1 >= len(STAGE_ORDER):
        return None
    adjusted = float(gdd_value) - float(offset)
    lower = float(boundaries[stage])
    upper = float(boundaries[STAGE_ORDER[idx + 1]])
    if upper <= lower:
        return None
    return float(np.clip((adjusted - lower) / (upper - lower), 0.0, 1.0))


def substage_label(stage: str, progress: float | None) -> str:
    base = STAGE_LABELS.get(stage, stage)
    if progress is None:
        return base
    if progress < 1 / 3:
        suffix = "early"
    elif progress < 2 / 3:
        suffix = "middle"
    else:
        suffix = "late"
    return f"{base} ({suffix})"


def predict_table(
    events_with_gdd: pd.DataFrame,
    model: MajorStageModel,
    evaluation: str,
    fold_id: str | None = None,
    crop_season_corrections: dict[str, float] | None = None,
    post_feedback_only: bool = False,
) -> pd.DataFrame:
    corrections = crop_season_corrections or {}
    rows = []
    for _, event in events_with_gdd.iterrows():
        key = scenario_key(event)
        if post_feedback_only and key not in corrections:
            continue
        code = event["source_variety_code"]
        boundaries = model.cultivar_boundaries.get(code, model.shared_boundaries)
        offset = model.cultivar_offsets.get(code, EMPIRICAL_CULTIVAR_OFFSETS.get(code, 0.0)) + corrections.get(key, 0.0)
        if pd.isna(event["GDDCUSUM"]):
            pred = None
            display_stage = None
            transition_flag = None
            progress = None
            display_substage = None
        else:
            pred, display_stage, transition_flag = display_stage_prediction(float(event["GDDCUSUM"]), boundaries, offset)
            progress = within_stage_progress(float(event["GDDCUSUM"]), boundaries, pred, offset)
            if transition_flag:
                display_substage = display_stage
            else:
                display_substage = substage_label(pred, progress)
        distance = None if pred is None else STAGE_RANK[pred] - int(event["major_stage_rank"])
        if display_stage is None:
            display_match = None
        elif "-" in display_stage:
            display_match = event["major_stage"] in display_stage.split("-")
        else:
            display_match = display_stage == event["major_stage"]
        rows.append(
            {
                "model": model.model,
                "biofix_rule": model.biofix_rule.name,
                "evaluation": evaluation,
                "fold_id": fold_id,
                **{column: event[column] for column in SCENARIO_COLUMNS},
                "source_variety_code": code,
                "BBCH_Principal": event["BBCH_Principal"],
                "observed_date": event["observed_date"],
                "biofix_date": event["biofix_date"],
                "observed_major_stage": event["major_stage"],
                "predicted_major_stage": pred,
                "display_major_stage": display_stage,
                "within_stage_progress": progress,
                "display_substage": display_substage,
                "transition_display": transition_flag,
                "stage_distance": distance,
                "abs_stage_distance": abs(distance) if distance is not None else None,
                "exact_major_stage_match": pred == event["major_stage"] if pred is not None else None,
                "display_major_stage_match": display_match,
                "adjacent_major_stage_match": abs(distance) <= 1 if distance is not None else None,
                "severe_misclassification": abs(distance) > 1 if distance is not None else None,
                "crop_season_correction_GDD": corrections.get(key, 0.0),
            }
        )
    return pd.DataFrame(rows)


def stage_interval_center(boundaries: dict[str, float], stage: str) -> float:
    idx = STAGE_RANK[stage]
    lower = boundaries[stage]
    if idx + 1 < len(STAGE_ORDER):
        upper = boundaries[STAGE_ORDER[idx + 1]]
        return float((lower + upper) / 2.0)
    return float(lower + 80.0)


def feedback_corrections(test_with_gdd: pd.DataFrame, model: MajorStageModel) -> tuple[dict[str, float], pd.DataFrame]:
    corrections = {}
    feedback_rows = []
    for scenario in scenario_records(test_with_gdd):
        key = scenario_key(scenario)
        sub = test_with_gdd.copy()
        for column, value in scenario.items():
            sub = sub[sub[column] == value]
        sub = sub.dropna(subset=["GDDCUSUM"]).sort_values("observed_date")
        sub = sub[sub["major_stage"] != "90"]
        if sub.empty:
            continue
        feedback = sub.iloc[0]
        code = feedback["source_variety_code"]
        boundaries = model.cultivar_boundaries.get(code, model.shared_boundaries)
        base_offset = model.cultivar_offsets.get(code, 0.0)
        config = CULTIVAR_SEARCH_CONFIG.get(code, CULTIVAR_SEARCH_CONFIG["JF"])
        limit = float(config["offset_limit"])
        step = float(config["offset_step"])
        grid = sorted(np.arange(-limit, limit + step, step), key=lambda value: abs(float(value)))
        correction = 0.0
        for candidate in grid:
            pred = predict_major_stage(float(feedback["GDDCUSUM"]), boundaries, base_offset + float(candidate))
            if pred == feedback["major_stage"]:
                correction = float(candidate)
                break
        corrections[key] = correction
        feedback_rows.append(
            {
                **scenario,
                "source_variety_code": code,
                "feedback_date": feedback["observed_date"],
                "feedback_major_stage": feedback["major_stage"],
                "season_correction_GDD": correction,
            }
        )
    return corrections, pd.DataFrame(feedback_rows)


def metrics(table: pd.DataFrame, exclude_stage90: bool = False) -> dict:
    valid = table.dropna(subset=["abs_stage_distance"]).copy()
    if exclude_stage90:
        valid = valid[valid["observed_major_stage"] != "90"].copy()
    if valid.empty:
        return {
            "n_events": 0,
            "mean_abs_stage_distance": math.nan,
            "exact_major_accuracy": math.nan,
            "adjacent_major_accuracy": math.nan,
            "severe_error_rate": math.nan,
        }
    return {
        "n_events": int(len(valid)),
        "mean_abs_stage_distance": float(valid["abs_stage_distance"].mean()),
        "exact_major_accuracy": float(valid["exact_major_stage_match"].mean()),
        "display_major_accuracy": float(valid["display_major_stage_match"].mean()),
        "transition_display_rate": float(valid["transition_display"].mean()),
        "adjacent_major_accuracy": float(valid["adjacent_major_stage_match"].mean()),
        "severe_error_rate": float(valid["severe_misclassification"].mean()),
    }


def scan_offset(observed: pd.DataFrame, boundaries: dict[str, float], code: str) -> float:
    if code in EMPIRICAL_CULTIVAR_OFFSETS:
        return EMPIRICAL_CULTIVAR_OFFSETS[code]
    config = CULTIVAR_SEARCH_CONFIG.get(code, CULTIVAR_SEARCH_CONFIG["JF"])
    limit = float(config["offset_limit"])
    step = float(config["offset_step"])
    grid = np.arange(-limit, limit + step, step)
    best_offset = 0.0
    best_score = math.inf
    for offset in grid:
        preds = observed["GDDCUSUM"].apply(lambda x: predict_major_stage(float(x), boundaries, float(offset)))
        distances = preds.map(STAGE_RANK).to_numpy(dtype=int) - observed["major_stage_rank"].to_numpy(dtype=int)
        score = float(np.mean(np.abs(distances)) + 0.02 * np.mean(np.abs(distances) > 1) + 0.001 * abs(offset))
        if score < best_score:
            best_score = score
            best_offset = float(offset)
    return best_offset


def fit_model(
    model_name: str,
    train_events: pd.DataFrame,
    weather_inputs: dict,
    prior: dict[str, float],
    rule: BiofixRule,
    use_cultivar_thresholds: bool,
    use_offsets: bool,
    min_cultivar_events: int,
    min_cultivar_stages: int,
) -> MajorStageModel:
    observed = attach_gdd(train_events, weather_inputs, rule).dropna(subset=["GDDCUSUM"]).copy()
    shared = calibrate_boundaries(observed, prior, step=10.0, prior_weight=2.0)
    cultivar_boundaries: dict[str, dict[str, float]] = {}
    cultivar_offsets: dict[str, float] = {}

    for code, group in observed.groupby("source_variety_code"):
        config = CULTIVAR_SEARCH_CONFIG.get(code, CULTIVAR_SEARCH_CONFIG["JF"])
        enough_data = len(group) >= min_cultivar_events and group["major_stage"].nunique() >= min_cultivar_stages
        if code in EMPIRICAL_CULTIVAR_BOUNDARIES:
            cultivar_boundaries[code] = EMPIRICAL_CULTIVAR_BOUNDARIES[code]
        elif use_cultivar_thresholds and enough_data:
            cultivar_boundaries[code] = calibrate_boundaries(
                group,
                shared,
                step=float(config["threshold_step"]),
                prior_weight=float(config["prior_weight"]),
            )
        else:
            cultivar_boundaries[code] = shared

        if use_offsets:
            cultivar_offsets[code] = scan_offset(group, cultivar_boundaries[code], code)
        else:
            cultivar_offsets[code] = EMPIRICAL_CULTIVAR_OFFSETS.get(code, 0.0)

    for code, offset in EMPIRICAL_CULTIVAR_OFFSETS.items():
        cultivar_offsets.setdefault(code, offset)
    for code, boundaries in EMPIRICAL_CULTIVAR_BOUNDARIES.items():
        cultivar_boundaries.setdefault(code, boundaries)

    return MajorStageModel(model_name, rule, shared, cultivar_boundaries, cultivar_offsets)


def mask_for_scenarios(events: pd.DataFrame, scenarios: list[dict]) -> pd.Series:
    mask = pd.Series(False, index=events.index)
    for scenario in scenarios:
        scenario_mask = pd.Series(True, index=events.index)
        for column, value in scenario.items():
            scenario_mask &= events[column] == value
        mask |= scenario_mask
    return mask


def site_year_folds(events: pd.DataFrame, n_folds: int, seed: int) -> list[list[dict]]:
    rng = np.random.default_rng(seed)
    folds: list[list[dict]] = [[] for _ in range(n_folds)]
    scenario_table = events[SCENARIO_COLUMNS + ["source_variety_code"]].drop_duplicates()
    for _, group in scenario_table.groupby("source_variety_code", sort=True):
        scenarios = group[SCENARIO_COLUMNS].to_dict(orient="records")
        order = list(rng.permutation(len(scenarios)))
        for position, scenario_index in enumerate(order):
            fold_loads = [len(fold) for fold in folds]
            preferred = (position + int(np.argmin(fold_loads))) % n_folds
            folds[preferred].append(scenarios[int(scenario_index)])
    return folds


def fold_id_for_scenarios(scenarios: list[dict], fold_index: int) -> str:
    return f"fold{fold_index}:" + "|".join(f"{item['site_id']}_{item['year']}_{item['variety']}" for item in scenarios)


def evaluate_cv(
    events: pd.DataFrame,
    weather_inputs: dict,
    prior: dict[str, float],
    folds: list[list[dict]],
    rule: BiofixRule,
    model_name: str,
    use_cultivar_thresholds: bool,
    use_offsets: bool,
    args: argparse.Namespace,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    frames = []
    feedback_frames = []
    fit_rows = []
    for fold_index, scenarios in enumerate(folds, start=1):
        test_mask = mask_for_scenarios(events, scenarios)
        train = events[~test_mask].copy()
        test = events[test_mask].copy()
        fold_id = fold_id_for_scenarios(scenarios, fold_index)
        model = fit_model(
            model_name,
            train,
            weather_inputs,
            prior,
            rule,
            use_cultivar_thresholds,
            use_offsets,
            args.min_cultivar_events,
            args.min_cultivar_stages,
        )
        test_with_gdd = attach_gdd(test, weather_inputs, rule)
        frames.append(predict_table(test_with_gdd, model, "3fold", fold_id))
        corrections, feedback = feedback_corrections(test_with_gdd, model)
        feedback["model"] = model_name
        feedback["fold_id"] = fold_id
        feedback_frames.append(feedback)
        post = test_with_gdd.merge(
            feedback[[*SCENARIO_COLUMNS, "feedback_date"]],
            on=SCENARIO_COLUMNS,
            how="left",
        )
        post = post[pd.to_datetime(post["observed_date"]) > pd.to_datetime(post["feedback_date"])].copy()
        frames.append(
            predict_table(
                post,
                model,
                "3fold_after_one_user_feedback",
                fold_id,
                crop_season_corrections=corrections,
                post_feedback_only=True,
            )
        )
        fit_rows.append(
            {
                "model": model_name,
                "fold_id": fold_id,
                "biofix_rule": rule.name,
                "use_cultivar_thresholds": use_cultivar_thresholds,
                "use_offsets": use_offsets,
                "n_train": int(len(train)),
                "n_test": int(len(test)),
                "shared_boundaries": json.dumps(model.shared_boundaries, ensure_ascii=False),
                "cultivar_boundaries": json.dumps(model.cultivar_boundaries, ensure_ascii=False),
                "cultivar_offsets": json.dumps(model.cultivar_offsets, ensure_ascii=False),
            }
        )
    return pd.concat(frames, ignore_index=True), pd.concat(feedback_frames, ignore_index=True), pd.DataFrame(fit_rows)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    events = load_observations(args.input)
    weather_inputs = build_weather_inputs_for_events(events, args.cache_dir)
    parameter_table = load_parameter_table(PHENO_DIR / "configs" / "BBCHGDD.json")
    prior = platform_major_prior(events, parameter_table)
    folds = site_year_folds(events, args.n_folds, args.seed)

    events.to_csv(args.output_dir / "major_stage_observations.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"major_stage": k, "label": STAGE_LABELS[k], "prior_GDD": v} for k, v in prior.items()]).to_csv(
        args.output_dir / "major_stage_prior_thresholds.csv", index=False, encoding="utf-8-sig"
    )

    model_specs = [
        ("shared_major_thresholds", False, False),
        ("shared_major_thresholds_cultivar_offset", False, True),
        ("cultivar_major_thresholds", True, False),
        ("cultivar_major_thresholds_offset", True, True),
    ]

    all_predictions = []
    all_feedback = []
    all_fits = []
    candidate_rows = []
    for rule in biofix_candidates():
        for model_name, use_cultivar_thresholds, use_offsets in model_specs:
            predictions, feedback, fits = evaluate_cv(
                events,
                weather_inputs,
                prior,
                folds,
                rule,
                model_name,
                use_cultivar_thresholds,
                use_offsets,
                args,
            )
            all_predictions.append(predictions)
            all_feedback.append(feedback)
            all_fits.append(fits)
            for evaluation, group in predictions.groupby("evaluation"):
                row = {
                    "model": model_name,
                    "biofix_rule": rule.name,
                    "evaluation": evaluation,
                    **{f"all_{k}": v for k, v in metrics(group, exclude_stage90=False).items()},
                    **{f"core_no90_{k}": v for k, v in metrics(group, exclude_stage90=True).items()},
                }
                candidate_rows.append(row)

    predictions = pd.concat(all_predictions, ignore_index=True)
    feedback = pd.concat(all_feedback, ignore_index=True)
    fits = pd.concat(all_fits, ignore_index=True)
    candidates = pd.DataFrame(candidate_rows).sort_values(
        [
            "evaluation",
            "core_no90_display_major_accuracy",
            "core_no90_exact_major_accuracy",
            "core_no90_adjacent_major_accuracy",
            "core_no90_mean_abs_stage_distance",
            "core_no90_severe_error_rate",
        ],
        ascending=[True, False, False, False, True, True],
    )

    predictions.to_csv(args.output_dir / "major_stage_validation_predictions.csv", index=False, encoding="utf-8-sig")
    feedback.to_csv(args.output_dir / "major_stage_user_feedback_simulation.csv", index=False, encoding="utf-8-sig")
    fits.to_csv(args.output_dir / "major_stage_cv_fitted_parameters.csv", index=False, encoding="utf-8-sig")
    candidates.to_csv(args.output_dir / "major_stage_candidate_summary.csv", index=False, encoding="utf-8-sig")

    selected = candidates[candidates["evaluation"] == "3fold"].iloc[0]
    selected_after_feedback = candidates[candidates["evaluation"] == "3fold_after_one_user_feedback"].iloc[0]
    selected_rule = {rule.name: rule for rule in biofix_candidates()}[str(selected["biofix_rule"])]
    selected_spec = {
        name: (use_cultivar_thresholds, use_offsets)
        for name, use_cultivar_thresholds, use_offsets in model_specs
    }[str(selected["model"])]
    final_model = fit_model(
        str(selected["model"]),
        events,
        weather_inputs,
        prior,
        selected_rule,
        selected_spec[0],
        selected_spec[1],
        args.min_cultivar_events,
        args.min_cultivar_stages,
    )
    final_rows = []
    for code in sorted(events["source_variety_code"].unique()):
        boundaries = final_model.cultivar_boundaries.get(code, final_model.shared_boundaries)
        offset = final_model.cultivar_offsets.get(code, 0.0)
        for stage in STAGE_ORDER:
            final_rows.append(
                {
                    "model": final_model.model,
                    "biofix_rule": final_model.biofix_rule.name,
                    "source_variety_code": code,
                    "major_stage": stage,
                    "major_stage_label": STAGE_LABELS[stage],
                    "boundary_GDD": boundaries[stage],
                    "cultivar_offset_GDD": offset,
                    "effective_boundary_GDD": boundaries[stage] + offset,
                }
            )
    pd.DataFrame(final_rows).to_csv(
        args.output_dir / "major_stage_deployable_parameters.csv", index=False, encoding="utf-8-sig"
    )

    metadata = {
        "approach": "deployable_major_stage_state_estimator",
        "stage_order": STAGE_ORDER,
        "stage_labels": STAGE_LABELS,
        "cultivar_search_config": CULTIVAR_SEARCH_CONFIG,
        "empirical_cultivar_offsets": EMPIRICAL_CULTIVAR_OFFSETS,
        "empirical_cultivar_boundaries": EMPIRICAL_CULTIVAR_BOUNDARIES,
        "transition_margin_GDD": TRANSITION_MARGIN_GDD,
        "n_observations": int(len(events)),
        "n_site_years": int(events[SCENARIO_COLUMNS].drop_duplicates().shape[0]),
        "n_folds": int(args.n_folds),
        "selected_without_feedback": selected.to_dict(),
        "selected_after_one_user_feedback": selected_after_feedback.to_dict(),
        "deployable_parameter_file": "major_stage_deployable_parameters.csv",
        "folds": [
            {"fold_id": fold_id_for_scenarios(fold, i), "site_years": fold}
            for i, fold in enumerate(folds, start=1)
        ],
    }
    (args.output_dir / "major_stage_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nBest 3-fold candidates:")
    print(candidates[candidates["evaluation"] == "3fold"].head(8).to_string(index=False))
    print("\nBest after one user feedback:")
    print(candidates[candidates["evaluation"] == "3fold_after_one_user_feedback"].head(8).to_string(index=False))
    print(f"\nWrote deployable major-stage outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
