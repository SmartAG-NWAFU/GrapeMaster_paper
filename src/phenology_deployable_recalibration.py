#!/usr/bin/env python3
"""Deployment-oriented recalibration for the GrapeMaster phenology module.

This analysis keeps a single BBCH prediction axis for the platform. It does not
split a separate disease-risk gate or fit stage-specific thermal models. The
only calibrated components are a meteorological biofix rule, one monotonic BBCH
threshold table, and small cultivar-level threshold offsets.
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
from scipy.optimize import differential_evolution


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

DEFAULT_OUTPUT_DIR = ROOT / "results" / "phenology_deployable"
MIN_STEP = 5.0
PRIOR_WEIGHT = 1.0


@dataclass(frozen=True)
class BiofixRule:
    name: str
    tmean_threshold: float | None
    run_days: int | None


@dataclass(frozen=True)
class DeployablePhenology:
    model: str
    biofix_rule: BiofixRule
    thresholds: dict[str, float]
    cultivar_offsets: dict[str, float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deployment-oriented BBCH recalibration.")
    parser.add_argument(
        "--input",
        type=Path,
        default=PHENO_DIR / "data" / "growth_stage_data.xlsx",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / "results" / "phenology" / "weather_cache",
    )
    parser.add_argument("--offset-limit", type=float, default=120.0)
    parser.add_argument("--offset-penalty", type=float, default=0.02)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def major_stage(bbch: str | None) -> str | None:
    if bbch is None:
        return None
    value = int(str(bbch).zfill(2))
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
    if value < 10:
        return "00"
    return None


def scenario_records(events: pd.DataFrame) -> list[dict]:
    return events[SCENARIO_COLUMNS].drop_duplicates().to_dict(orient="records")


def load_observations(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path)
    raw["date"] = pd.to_datetime(raw["date"])
    raw["year"] = raw["date"].dt.year.astype(int)
    observed = raw.dropna(subset=["growth_stage"]).copy()
    observed["BBCH_Principal"] = observed["growth_stage"].astype(int).astype(str).str.zfill(2)
    observed = observed[observed["BBCH_Principal"] != "00"].copy()

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
                "major_stage": major_stage(row["BBCH_Principal"]),
                "observed_date": row["date"].strftime("%Y-%m-%d"),
            }
        )
    return pd.DataFrame(rows).sort_values(SCENARIO_COLUMNS + ["observed_date", "BBCH_Principal"]).reset_index(drop=True)


def build_weather_inputs_for_events(events: pd.DataFrame, cache_dir: Path) -> dict:
    obs = events[SCENARIO_COLUMNS + ["BBCH_Principal", "observed_date"]].copy()
    return build_weather_inputs(obs, cache_dir)


def platform_prior(events: pd.DataFrame, parameter_table: dict) -> dict[str, float]:
    platform_stages: set[str] = set()
    for scenario in scenario_records(events):
        thresholds = get_thresholds(
            scenario["province"],
            scenario["variety"],
            scenario["maturation"],
            parameter_table=parameter_table,
        )
        platform_stages.update(thresholds["GS"].astype(str).str.zfill(2).tolist())
    observed_stages = set(events["BBCH_Principal"].astype(str).str.zfill(2).tolist())
    stages = sorted(platform_stages | observed_stages, key=lambda x: int(x))

    values: dict[str, list[float]] = {stage: [] for stage in stages}
    for scenario in scenario_records(events):
        thresholds = get_thresholds(
            scenario["province"],
            scenario["variety"],
            scenario["maturation"],
            parameter_table=parameter_table,
        )
        xs = thresholds["GS"].astype(int).to_numpy(dtype=float)
        ys = thresholds["GDD"].astype(float).to_numpy()
        for stage in stages:
            stage_num = float(int(stage))
            if stage_num <= xs.min():
                slope = (ys[1] - ys[0]) / (xs[1] - xs[0])
                value = ys[0] + (stage_num - xs[0]) * slope
            elif stage_num >= xs.max():
                slope = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
                value = ys[-1] + (stage_num - xs[-1]) * slope
            else:
                value = np.interp(stage_num, xs, ys)
            values[stage].append(max(0.0, float(value)))
    return {stage: float(np.median(v)) for stage, v in values.items()}


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

    active = pd.Series(True, index=df.index)
    biofix_date = df["date_dt"].min()
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
    return df[["Date", "temperature_2m_mean", "biofix_date", "GDD", "GDDCUSUM"]]


def gdd_on_observation_dates(events: pd.DataFrame, weather_inputs: dict, rule: BiofixRule) -> pd.DataFrame:
    frames = []
    for scenario in scenario_records(events):
        key = scenario_key(scenario)
        gdd = daily_gdd(weather_inputs[key], rule)
        sub = events.copy()
        for column, value in scenario.items():
            sub = sub[sub[column] == value]
        merged = sub.merge(gdd[["Date", "biofix_date", "GDDCUSUM"]], left_on="observed_date", right_on="Date", how="left")
        frames.append(merged.drop(columns=["Date"]))
    return pd.concat(frames, ignore_index=True)


def pava_increasing(stages: list[str], values: dict[str, float], weights: dict[str, float]) -> dict[str, float]:
    blocks = []
    for stage in stages:
        w = max(float(weights.get(stage, 1.0)), 1e-6)
        blocks.append({"stages": [stage], "sum_w": w, "sum_y": w * float(values[stage])})
        while len(blocks) >= 2:
            left = blocks[-2]["sum_y"] / blocks[-2]["sum_w"]
            right = blocks[-1]["sum_y"] / blocks[-1]["sum_w"]
            if left <= right:
                break
            b = blocks.pop()
            blocks[-1]["stages"].extend(b["stages"])
            blocks[-1]["sum_w"] += b["sum_w"]
            blocks[-1]["sum_y"] += b["sum_y"]

    out = {}
    for block in blocks:
        value = block["sum_y"] / block["sum_w"]
        for stage in block["stages"]:
            out[stage] = float(value)

    ordered = sorted(stages, key=lambda x: int(x))
    last = None
    for stage in ordered:
        value = out[stage]
        if last is not None and value <= last:
            value = last + MIN_STEP
        out[stage] = float(max(0.0, value))
        last = out[stage]
    return out


def _calibrate_thresholds_from_adjusted_gdd(observed: pd.DataFrame, prior_thresholds: dict[str, float]) -> dict[str, float]:
    stages = sorted(prior_thresholds, key=lambda x: int(x))
    targets = {}
    weights = {}
    for stage in stages:
        group = observed[observed["BBCH_Principal"] == stage]
        if group.empty:
            targets[stage] = prior_thresholds[stage]
            weights[stage] = PRIOR_WEIGHT
        else:
            n = len(group)
            median = float(group["adjusted_GDDCUSUM"].median())
            targets[stage] = (n * median + PRIOR_WEIGHT * prior_thresholds[stage]) / (n + PRIOR_WEIGHT)
            weights[stage] = n + PRIOR_WEIGHT
    return pava_increasing(stages, targets, weights)


def fit_model(
    model_name: str,
    train_events: pd.DataFrame,
    weather_inputs: dict,
    prior_thresholds: dict[str, float],
    biofix_rule: BiofixRule,
    offset_limit: float,
    use_offsets: bool,
    offset_penalty: float = 0.02,
    seed: int = 42,
) -> DeployablePhenology:
    observed = gdd_on_observation_dates(train_events, weather_inputs, biofix_rule).dropna(subset=["GDDCUSUM"]).copy()
    cultivar_codes = sorted(train_events["source_variety_code"].unique())

    def build_with_offsets(offset_values: np.ndarray) -> DeployablePhenology:
        offsets = {code: float(value) for code, value in zip(cultivar_codes, offset_values)}
        observed["current_offset"] = observed["source_variety_code"].map(offsets).fillna(0.0)
        observed["adjusted_GDDCUSUM"] = observed["GDDCUSUM"] - observed["current_offset"]
        thresholds = _calibrate_thresholds_from_adjusted_gdd(observed, prior_thresholds)
        return DeployablePhenology(model_name, biofix_rule, thresholds, offsets)

    if (not use_offsets) or (not cultivar_codes):
        return build_with_offsets(np.zeros(len(cultivar_codes), dtype=float))

    def objective(x: np.ndarray) -> float:
        model = build_with_offsets(np.asarray(x, dtype=float))
        dates = evaluate_first_dates(model, train_events, weather_inputs, "train")
        states = evaluate_state(model, train_events, weather_inputs, "train")
        dm = date_metrics(dates)
        sm = state_metrics(states)
        if math.isnan(dm["mae_days"]) or math.isnan(sm["mean_abs_stage_distance"]):
            return 1e6
        penalty = float(offset_penalty) * float(np.mean(np.abs(x)))
        return float(dm["mae_days"] + 2.0 * sm["mean_abs_stage_distance"] + penalty)

    result = differential_evolution(
        objective,
        bounds=[(-float(offset_limit), float(offset_limit)) for _ in cultivar_codes],
        seed=int(seed),
        maxiter=35,
        popsize=8,
        polish=True,
        updating="immediate",
        workers=1,
        tol=0.01,
    )
    clipped = np.clip(np.asarray(result.x, dtype=float), -float(offset_limit), float(offset_limit))
    return build_with_offsets(clipped)


def predicted_stage(gdd_value: float, thresholds: dict[str, float], offset: float) -> str | None:
    current = None
    for stage in sorted(thresholds, key=lambda x: int(x)):
        if gdd_value >= thresholds[stage] + offset:
            current = stage
        else:
            break
    return current


def predicted_date(gdd: pd.DataFrame, threshold: float) -> str | None:
    hit = gdd[gdd["GDDCUSUM"] >= threshold]
    if hit.empty:
        return None
    return str(hit.iloc[0]["Date"])


def evaluate_state(model: DeployablePhenology, events: pd.DataFrame, weather_inputs: dict, evaluation: str, fold_id: str | None = None) -> pd.DataFrame:
    rows = []
    ordered = sorted(model.thresholds, key=lambda x: int(x))
    rank = {stage: i for i, stage in enumerate(ordered)}
    for scenario in scenario_records(events):
        key = scenario_key(scenario)
        gdd = daily_gdd(weather_inputs[key], model.biofix_rule)
        sub = events.copy()
        for column, value in scenario.items():
            sub = sub[sub[column] == value]
        merged = sub.merge(gdd[["Date", "biofix_date", "GDDCUSUM"]], left_on="observed_date", right_on="Date", how="left")
        for _, event in merged.iterrows():
            obs_stage = str(event["BBCH_Principal"]).zfill(2)
            offset = model.cultivar_offsets.get(event["source_variety_code"], 0.0)
            pred_stage = None if pd.isna(event["GDDCUSUM"]) else predicted_stage(float(event["GDDCUSUM"]), model.thresholds, offset)
            stage_distance = None
            if pred_stage in rank and obs_stage in rank:
                stage_distance = int(rank[pred_stage] - rank[obs_stage])
            rows.append(
                {
                    "model": model.model,
                    "evaluation": evaluation,
                    "fold_id": fold_id,
                    **{column: event[column] for column in SCENARIO_COLUMNS},
                    "source_variety_code": event["source_variety_code"],
                    "BBCH_Principal": obs_stage,
                    "observed_date": event["observed_date"],
                    "biofix_date": event["biofix_date"],
                    "observed_major_stage": major_stage(obs_stage),
                    "predicted_BBCH_Principal": pred_stage,
                    "predicted_major_stage": major_stage(pred_stage),
                    "stage_distance": stage_distance,
                    "abs_stage_distance": abs(stage_distance) if stage_distance is not None else None,
                    "exact_state_match": pred_stage == obs_stage if pred_stage is not None else None,
                    "adjacent_state_match": abs(stage_distance) <= 1 if stage_distance is not None else None,
                    "major_stage_match": major_stage(pred_stage) == major_stage(obs_stage) if pred_stage is not None else None,
                }
            )
    return pd.DataFrame(rows)


def first_events(events: pd.DataFrame) -> pd.DataFrame:
    return (
        events.sort_values("observed_date")
        .drop_duplicates(SCENARIO_COLUMNS + ["BBCH_Principal"], keep="first")
        .reset_index(drop=True)
    )


def evaluate_first_dates(model: DeployablePhenology, events: pd.DataFrame, weather_inputs: dict, evaluation: str, fold_id: str | None = None) -> pd.DataFrame:
    event_table = first_events(events)
    rows = []
    for scenario in scenario_records(event_table):
        key = scenario_key(scenario)
        gdd = daily_gdd(weather_inputs[key], model.biofix_rule)
        sub = event_table.copy()
        for column, value in scenario.items():
            sub = sub[sub[column] == value]
        for _, event in sub.iterrows():
            stage = str(event["BBCH_Principal"]).zfill(2)
            offset = model.cultivar_offsets.get(event["source_variety_code"], 0.0)
            threshold = model.thresholds.get(stage)
            pred = None if threshold is None else predicted_date(gdd, threshold + offset)
            error = None if pred is None else (pd.to_datetime(pred) - pd.to_datetime(event["observed_date"])).days
            rows.append(
                {
                    "model": model.model,
                    "evaluation": evaluation,
                    "fold_id": fold_id,
                    **{column: event[column] for column in SCENARIO_COLUMNS},
                    "source_variety_code": event["source_variety_code"],
                    "BBCH_Principal": stage,
                    "major_stage": event["major_stage"],
                    "observed_date": event["observed_date"],
                    "predicted_date": pred,
                    "error_days": error,
                    "abs_error_days": abs(error) if error is not None else None,
                }
            )
    return pd.DataFrame(rows)


def date_metrics(table: pd.DataFrame) -> dict:
    valid = table.dropna(subset=["abs_error_days"]).copy()
    if valid.empty:
        return {"n_events": int(len(table)), "n_matched": 0, "mae_days": math.nan, "rmse_days": math.nan, "bias_days": math.nan, "within_7_days": math.nan, "within_14_days": math.nan}
    err = valid["error_days"].astype(float)
    abs_err = valid["abs_error_days"].astype(float)
    return {
        "n_events": int(len(table)),
        "n_matched": int(len(valid)),
        "mae_days": float(abs_err.mean()),
        "rmse_days": float(np.sqrt(np.mean(np.square(err)))),
        "bias_days": float(err.mean()),
        "within_7_days": float((abs_err <= 7).mean()),
        "within_14_days": float((abs_err <= 14).mean()),
    }


def state_metrics(table: pd.DataFrame) -> dict:
    valid = table.dropna(subset=["abs_stage_distance"]).copy()
    if valid.empty:
        return {"n_events": int(len(table)), "n_matched": 0, "mean_abs_stage_distance": math.nan, "exact_state_accuracy": math.nan, "adjacent_state_accuracy": math.nan, "major_stage_accuracy": math.nan}
    return {
        "n_events": int(len(table)),
        "n_matched": int(len(valid)),
        "mean_abs_stage_distance": float(valid["abs_stage_distance"].mean()),
        "exact_state_accuracy": float(valid["exact_state_match"].mean()),
        "adjacent_state_accuracy": float(valid["adjacent_state_match"].mean()),
        "major_stage_accuracy": float(valid["major_stage_match"].mean()),
    }


def run_losyo(
    events: pd.DataFrame,
    weather_inputs: dict,
    prior: dict[str, float],
    rule: BiofixRule,
    offset_limit: float,
    use_offsets: bool,
    offset_penalty: float,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    state_frames = []
    date_frames = []
    for heldout in scenario_records(events):
        mask = pd.Series(True, index=events.index)
        for column, value in heldout.items():
            mask &= events[column] == value
        train = events[~mask].copy()
        test = events[mask].copy()
        fold_id = f"{heldout['site_id']}_{heldout['year']}_{heldout['variety']}"
        model = fit_model(
            "deployable_recalibrated",
            train,
            weather_inputs,
            prior,
            rule,
            offset_limit,
            use_offsets,
            offset_penalty=offset_penalty,
            seed=seed + len(state_frames) + 1,
        )
        state_frames.append(evaluate_state(model, test, weather_inputs, "losyo", fold_id))
        date_frames.append(evaluate_first_dates(model, test, weather_inputs, "losyo", fold_id))
    return pd.concat(state_frames, ignore_index=True), pd.concat(date_frames, ignore_index=True)


def baseline_model(prior: dict[str, float]) -> DeployablePhenology:
    return DeployablePhenology("baseline_interpolated", BiofixRule("jan1", None, None), prior, {})


def choose_candidate(
    events: pd.DataFrame,
    weather_inputs: dict,
    prior: dict[str, float],
    offset_limit: float,
    offset_penalty: float,
    seed: int,
) -> pd.DataFrame:
    rows = []
    for rule in biofix_candidates():
        for use_offsets in [False, True]:
            state, dates = run_losyo(events, weather_inputs, prior, rule, offset_limit, use_offsets, offset_penalty, seed)
            sm = state_metrics(state)
            dm = date_metrics(dates)
            rows.append(
                {
                    "biofix_rule": rule.name,
                    "use_cultivar_offsets": bool(use_offsets),
                    **{f"state_{k}": v for k, v in sm.items()},
                    **{f"date_{k}": v for k, v in dm.items()},
                }
            )
    out = pd.DataFrame(rows)
    out = out.sort_values(
        ["state_major_stage_accuracy", "state_adjacent_state_accuracy", "date_mae_days"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    return out


def write_calibrated_parameter_table(model: DeployablePhenology, prior_parameter_table: dict, output_path: Path) -> None:
    copied = json.loads(json.dumps(prior_parameter_table, ensure_ascii=False))
    for code, mapped in VARIETY_MAP.items():
        key = mapped["variety"]
        if key not in copied["GuangXi"]:
            key = mapped["maturation"]
        offset = model.cultivar_offsets.get(code, 0.0)
        records = [
            {"GS": stage, "GDD": round(max(0.0, value + offset), 6)}
            for stage, value in sorted(model.thresholds.items(), key=lambda item: int(item[0]))
        ]
        copied["GuangXi"][key]["BBCHGDD"] = records
    output_path.write_text(json.dumps(copied, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    events = load_observations(args.input)
    parameter_table = load_parameter_table(PHENO_DIR / "configs" / "BBCHGDD.json")
    prior = platform_prior(events, parameter_table)
    weather_inputs = build_weather_inputs_for_events(events, args.cache_dir)

    events.to_csv(args.output_dir / "phenology_deployable_observations.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"BBCH_Principal": k, "prior_GDD": v} for k, v in sorted(prior.items(), key=lambda item: int(item[0]))]).to_csv(
        args.output_dir / "phenology_deployable_prior_thresholds.csv", index=False, encoding="utf-8-sig"
    )

    candidates = choose_candidate(events, weather_inputs, prior, args.offset_limit, args.offset_penalty, args.seed)
    candidates.to_csv(args.output_dir / "phenology_deployable_candidate_summary.csv", index=False, encoding="utf-8-sig")

    best_row = candidates.iloc[0]
    rule_map = {r.name: r for r in biofix_candidates()}
    best_rule = rule_map[str(best_row["biofix_rule"])]
    use_offsets = bool(best_row["use_cultivar_offsets"])

    base = baseline_model(prior)
    final = fit_model(
        "deployable_recalibrated",
        events,
        weather_inputs,
        prior,
        best_rule,
        args.offset_limit,
        use_offsets,
        offset_penalty=args.offset_penalty,
        seed=args.seed,
    )

    state = pd.concat(
        [
            evaluate_state(base, events, weather_inputs, "resubstitution"),
            evaluate_state(final, events, weather_inputs, "resubstitution"),
            run_losyo(events, weather_inputs, prior, best_rule, args.offset_limit, use_offsets, args.offset_penalty, args.seed)[0],
        ],
        ignore_index=True,
    )
    dates = pd.concat(
        [
            evaluate_first_dates(base, events, weather_inputs, "resubstitution"),
            evaluate_first_dates(final, events, weather_inputs, "resubstitution"),
            run_losyo(events, weather_inputs, prior, best_rule, args.offset_limit, use_offsets, args.offset_penalty, args.seed)[1],
        ],
        ignore_index=True,
    )

    state.to_csv(args.output_dir / "phenology_deployable_state_validation.csv", index=False, encoding="utf-8-sig")
    dates.to_csv(args.output_dir / "phenology_deployable_first_date_validation.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [
            {"model": final.model, "BBCH_Principal": stage, "GDD": value}
            for stage, value in sorted(final.thresholds.items(), key=lambda item: int(item[0]))
        ]
    ).to_csv(args.output_dir / "phenology_deployable_calibrated_thresholds.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame([{"source_variety_code": k, "offset_GDD": v} for k, v in final.cultivar_offsets.items()]).to_csv(
        args.output_dir / "phenology_deployable_cultivar_offsets.csv", index=False, encoding="utf-8-sig"
    )
    write_calibrated_parameter_table(final, parameter_table, args.output_dir / "BBCHGDD_deployable_recalibrated.json")

    summary_rows = []
    for (model, evaluation), group in state.groupby(["model", "evaluation"]):
        summary_rows.append({"metric_level": "observed_date_state", "model": model, "evaluation": evaluation, **state_metrics(group)})
    for (model, evaluation), group in dates.groupby(["model", "evaluation"]):
        summary_rows.append({"metric_level": "first_observed_stage_date", "model": model, "evaluation": evaluation, **date_metrics(group)})
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(args.output_dir / "phenology_deployable_summary.csv", index=False, encoding="utf-8-sig")

    metadata = {
        "approach": "single_axis_deployment_recalibration",
        "thermal_response": ThermalParams().as_dict(),
        "selected_biofix_rule": final.biofix_rule.__dict__,
        "use_cultivar_offsets": use_offsets,
        "offset_limit_GDD": args.offset_limit,
        "offset_penalty": args.offset_penalty,
        "offset_calibration": "directly optimized cultivar-level global offsets with shared monotonic thresholds",
        "n_observations_excluding_bbch00": int(len(events)),
        "n_site_years": int(events[SCENARIO_COLUMNS].drop_duplicates().shape[0]),
        "observed_stages": sorted(events["BBCH_Principal"].unique(), key=lambda x: int(x)),
        "output_parameter_table": "BBCHGDD_deployable_recalibrated.json",
    }
    (args.output_dir / "phenology_deployable_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("\nCandidate ranking:")
    print(candidates.head(10).to_string(index=False))
    print("\nValidation summary:")
    print(summary.to_string(index=False))
    print(f"\nWrote deployment-oriented phenology outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
