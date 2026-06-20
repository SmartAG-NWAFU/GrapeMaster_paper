#!/usr/bin/env python3
"""Full-stage calibration for the standalone GrapeMaster phenology module.

This v2 analysis treats the phenology module as a standalone temperature-driven
predictor. It uses all observed BBCH stages except BBCH 00, calibrates a shared
Wang-Engel thermal response plus full-stage thresholds under monotonic
constraints, and optionally adds cultivar-level threshold offsets. Cross-
validation is grouped by site-year and defaults to 3 folds to keep the
calibration tractable on the small Guangxi validation set.
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

THERMAL_BOUNDS = [(5.0, 12.0), (25.0, 35.0), (38.0, 45.0)]
DEFAULT_OFFSET_LIMIT = 150.0
PRIOR_WEIGHT = 1.0
MIN_THRESHOLD_STEP = 0.1
MAJOR_STAGE_LABELS = {
    "10": "Leaf development",
    "50": "Inflorescence emergence",
    "60": "Flowering",
    "70": "Berry development",
    "80": "Ripening",
    "90": "Senescence or post-harvest",
}


@dataclass(frozen=True)
class FittedPhenology:
    model_name: str
    thermal_params: ThermalParams
    thresholds: dict[str, float]
    cultivar_offsets: dict[str, float]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Full-stage phenology calibration v2.")
    parser.add_argument(
        "--input",
        type=Path,
        default=PHENO_DIR / "data" / "growth_stage_data.xlsx",
        help="Raw phenology observation Excel file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "phenology_v2_3fold",
        help="Output directory.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / "results" / "phenology" / "weather_cache",
        help="Weather cache directory. Defaults to the cache from the v1 analysis.",
    )
    parser.add_argument("--maxiter", type=int, default=8, help="Differential-evolution iterations.")
    parser.add_argument("--popsize", type=int, default=4, help="Differential-evolution population size.")
    parser.add_argument("--offset-limit", type=float, default=DEFAULT_OFFSET_LIMIT, help="Cultivar GDD offset bound.")
    parser.add_argument("--n-folds", type=int, default=3, help="Grouped site-year cross-validation folds.")
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def scenario_records(events: pd.DataFrame) -> list[dict]:
    return events[SCENARIO_COLUMNS].drop_duplicates().to_dict(orient="records")


def major_stage(bbch: str) -> str | None:
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
    return None


def load_first_observed_events(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path)
    raw["date"] = pd.to_datetime(raw["date"])
    raw["year"] = raw["date"].dt.year.astype(int)
    observed = raw.dropna(subset=["growth_stage"]).copy()
    observed["BBCH_Principal"] = observed["growth_stage"].astype(int).astype(str).str.zfill(2)

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
    events = pd.DataFrame(rows).sort_values("observed_date")
    events = events.drop_duplicates(SCENARIO_COLUMNS + ["BBCH_Principal"], keep="first")
    events = events[events["BBCH_Principal"] != "00"].reset_index(drop=True)
    return events


def build_weather_inputs_for_events(events: pd.DataFrame, cache_dir: Path) -> dict:
    obs = events[SCENARIO_COLUMNS + ["BBCH_Principal", "observed_date"]].copy()
    return build_weather_inputs(obs, cache_dir)


def daily_gdd(weather_rows: list[dict], params: ThermalParams) -> pd.DataFrame:
    rows = pd.DataFrame(weather_rows).copy()
    rows["Date"] = pd.to_datetime(rows["Date"]).dt.strftime("%Y-%m-%d")
    rows["GDD"] = rows["temperature_2m_mean"].apply(lambda x: wang_engel(float(x), params))
    rows["GDDCUSUM"] = rows["GDD"].cumsum()
    return rows[["Date", "temperature_2m_mean", "GDD", "GDDCUSUM"]]


def gdd_table_for_events(events: pd.DataFrame, weather_inputs: dict, params: ThermalParams) -> pd.DataFrame:
    frames = []
    for scenario in scenario_records(events):
        key = scenario_key(scenario)
        gdd = daily_gdd(weather_inputs[key], params)
        scenario_events = events.copy()
        for column, value in scenario.items():
            scenario_events = scenario_events[scenario_events[column] == value]
        merged = scenario_events.merge(
            gdd[["Date", "GDDCUSUM"]],
            left_on="observed_date",
            right_on="Date",
            how="left",
        ).drop(columns=["Date"])
        frames.append(merged)
    return pd.concat(frames, ignore_index=True)


def platform_threshold_prior(events: pd.DataFrame, parameter_table: dict) -> dict[str, float]:
    stages = sorted(events["BBCH_Principal"].unique(), key=lambda x: int(x))
    priors_by_stage: dict[str, list[float]] = {stage: [] for stage in stages}
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
                value = float(ys[0] + (stage_num - xs[0]) * ((ys[1] - ys[0]) / (xs[1] - xs[0])))
            elif stage_num >= xs.max():
                value = float(ys[-1] + (stage_num - xs[-1]) * ((ys[-1] - ys[-2]) / (xs[-1] - xs[-2])))
            else:
                value = float(np.interp(stage_num, xs, ys))
            priors_by_stage[stage].append(max(0.0, value))
    return {stage: float(np.median(values)) for stage, values in priors_by_stage.items()}


def enforce_monotonic(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values, key=lambda x: int(x))
    fixed = {}
    last = None
    for stage in ordered:
        value = float(values[stage])
        if last is not None and value <= last:
            value = last + MIN_THRESHOLD_STEP
        fixed[stage] = value
        last = value
    return fixed


def calibrate_thresholds(
    train_events: pd.DataFrame,
    weather_inputs: dict,
    params: ThermalParams,
    prior_thresholds: dict[str, float],
    with_cultivar_offsets: bool,
    offset_limit: float,
) -> tuple[dict[str, float], dict[str, float]]:
    observed = gdd_table_for_events(train_events, weather_inputs, params).dropna(subset=["GDDCUSUM"])
    threshold_values = {}
    for stage in prior_thresholds:
        group = observed[observed["BBCH_Principal"] == stage]
        if group.empty:
            threshold_values[stage] = prior_thresholds[stage]
            continue
        median_gdd = float(group["GDDCUSUM"].median())
        n = len(group)
        threshold_values[stage] = (n * median_gdd + PRIOR_WEIGHT * prior_thresholds[stage]) / (n + PRIOR_WEIGHT)
    thresholds = enforce_monotonic(threshold_values)

    offsets = {code: 0.0 for code in sorted(train_events["source_variety_code"].unique())}
    if not with_cultivar_offsets:
        return thresholds, offsets

    observed["base_threshold"] = observed["BBCH_Principal"].map(thresholds)
    observed["residual_gdd"] = observed["GDDCUSUM"] - observed["base_threshold"]
    for code, group in observed.groupby("source_variety_code"):
        if group[SCENARIO_COLUMNS].drop_duplicates().shape[0] < 2:
            offsets[code] = 0.0
            continue
        offsets[code] = float(np.clip(group["residual_gdd"].median(), -offset_limit, offset_limit))
    return thresholds, offsets


def predicted_date_for_stage(gdd: pd.DataFrame, threshold: float) -> str | None:
    reached = gdd[gdd["GDDCUSUM"] >= threshold]
    if reached.empty:
        return None
    return str(reached.iloc[0]["Date"])


def simulated_stage_on_date(gdd: pd.DataFrame, thresholds: dict[str, float], date: str, offset: float) -> str | None:
    row = gdd[gdd["Date"] == date]
    if row.empty:
        return None
    value = float(row.iloc[0]["GDDCUSUM"])
    current = None
    for stage in sorted(thresholds, key=lambda x: int(x)):
        if value >= thresholds[stage] + offset:
            current = stage
        else:
            break
    return current


def evaluate_exact(
    model: FittedPhenology,
    events: pd.DataFrame,
    weather_inputs: dict,
    evaluation: str,
    fold_id: str | None = None,
) -> pd.DataFrame:
    rows = []
    for scenario in scenario_records(events):
        key = scenario_key(scenario)
        gdd = daily_gdd(weather_inputs[key], model.thermal_params)
        scenario_events = events.copy()
        for column, value in scenario.items():
            scenario_events = scenario_events[scenario_events[column] == value]
        for _, event in scenario_events.iterrows():
            stage = str(event["BBCH_Principal"]).zfill(2)
            offset = model.cultivar_offsets.get(event["source_variety_code"], 0.0)
            threshold = model.thresholds.get(stage)
            predicted = None if threshold is None else predicted_date_for_stage(gdd, threshold + offset)
            error = None if predicted is None else (pd.to_datetime(predicted) - pd.to_datetime(event["observed_date"])).days
            sim_stage = simulated_stage_on_date(gdd, model.thresholds, event["observed_date"], offset)
            rows.append(
                {
                    "model": model.model_name,
                    "evaluation": evaluation,
                    "fold_id": fold_id,
                    **{column: event[column] for column in SCENARIO_COLUMNS},
                    "source_variety_code": event["source_variety_code"],
                    "BBCH_Principal": stage,
                    "major_stage": event["major_stage"],
                    "observed_date": event["observed_date"],
                    "predicted_date": predicted,
                    "error_days": error,
                    "abs_error_days": abs(error) if error is not None else None,
                    "simulated_stage_on_observed_date": sim_stage,
                    "major_stage_match_on_observed_date": (
                        major_stage(sim_stage) == event["major_stage"] if sim_stage and event["major_stage"] else None
                    ),
                }
            )
    return pd.DataFrame(rows)


def evaluate_major_first_dates(
    model: FittedPhenology,
    events: pd.DataFrame,
    weather_inputs: dict,
    evaluation: str,
    fold_id: str | None = None,
) -> pd.DataFrame:
    major_events = (
        events.dropna(subset=["major_stage"])
        .sort_values("observed_date")
        .drop_duplicates(SCENARIO_COLUMNS + ["major_stage"], keep="first")
    )
    rows = []
    for scenario in scenario_records(major_events):
        key = scenario_key(scenario)
        gdd = daily_gdd(weather_inputs[key], model.thermal_params)
        scenario_events = major_events.copy()
        for column, value in scenario.items():
            scenario_events = scenario_events[scenario_events[column] == value]
        for _, event in scenario_events.iterrows():
            offset = model.cultivar_offsets.get(event["source_variety_code"], 0.0)
            stage_thresholds = [
                value + offset for stage, value in model.thresholds.items() if major_stage(stage) == event["major_stage"]
            ]
            predicted = None if not stage_thresholds else predicted_date_for_stage(gdd, min(stage_thresholds))
            error = None if predicted is None else (pd.to_datetime(predicted) - pd.to_datetime(event["observed_date"])).days
            rows.append(
                {
                    "model": model.model_name,
                    "evaluation": evaluation,
                    "fold_id": fold_id,
                    **{column: event[column] for column in SCENARIO_COLUMNS},
                    "source_variety_code": event["source_variety_code"],
                    "major_stage": event["major_stage"],
                    "major_stage_label": MAJOR_STAGE_LABELS.get(event["major_stage"]),
                    "observed_date": event["observed_date"],
                    "predicted_date": predicted,
                    "error_days": error,
                    "abs_error_days": abs(error) if error is not None else None,
                }
            )
    return pd.DataFrame(rows)


def metric_dict(table: pd.DataFrame) -> dict:
    matched = table.dropna(subset=["abs_error_days"]).copy()
    if matched.empty:
        return {
            "n_events": len(table),
            "n_matched": 0,
            "mae_days": math.nan,
            "rmse_days": math.nan,
            "bias_days": math.nan,
            "within_7_days": math.nan,
            "within_14_days": math.nan,
        }
    errors = matched["error_days"].astype(float)
    abs_errors = matched["abs_error_days"].astype(float)
    return {
        "n_events": int(len(table)),
        "n_matched": int(len(matched)),
        "mae_days": float(abs_errors.mean()),
        "rmse_days": float(np.sqrt(np.mean(np.square(errors)))),
        "bias_days": float(errors.mean()),
        "within_7_days": float((abs_errors <= 7).mean()),
        "within_14_days": float((abs_errors <= 14).mean()),
    }


def fit_model(
    model_name: str,
    train_events: pd.DataFrame,
    weather_inputs: dict,
    prior_thresholds: dict[str, float],
    with_cultivar_offsets: bool,
    offset_limit: float,
    maxiter: int,
    popsize: int,
    seed: int,
) -> FittedPhenology:
    def objective(x: np.ndarray) -> float:
        tbase, topt, tceil = [float(v) for v in x]
        if not (tbase < topt < tceil):
            return 1e6
        params = ThermalParams(tbase, topt, tceil)
        thresholds, offsets = calibrate_thresholds(
            train_events, weather_inputs, params, prior_thresholds, with_cultivar_offsets, offset_limit
        )
        model = FittedPhenology(model_name, params, thresholds, offsets)
        exact = evaluate_exact(model, train_events, weather_inputs, "train")
        score = metric_dict(exact)["mae_days"]
        if math.isnan(score):
            return 1e6
        offset_penalty = 0.01 * float(np.mean([abs(v) for v in offsets.values()])) if offsets else 0.0
        return score + offset_penalty

    result = differential_evolution(
        objective,
        bounds=THERMAL_BOUNDS,
        maxiter=maxiter,
        popsize=popsize,
        seed=seed,
        polish=True,
        updating="immediate",
        workers=1,
    )
    params = ThermalParams(*[float(v) for v in result.x])
    thresholds, offsets = calibrate_thresholds(
        train_events, weather_inputs, params, prior_thresholds, with_cultivar_offsets, offset_limit
    )
    return FittedPhenology(model_name, params, thresholds, offsets)


def baseline_model(events: pd.DataFrame, parameter_table: dict) -> FittedPhenology:
    thresholds = platform_threshold_prior(events, parameter_table)
    return FittedPhenology("baseline_interpolated", ThermalParams(), thresholds, {})


def site_year_folds(events: pd.DataFrame, n_folds: int, seed: int) -> list[list[dict]]:
    scenarios = scenario_records(events)
    if n_folds < 2:
        raise ValueError("--n-folds must be at least 2.")
    if n_folds > len(scenarios):
        raise ValueError(f"--n-folds={n_folds} exceeds the {len(scenarios)} available site-years.")

    rng = np.random.default_rng(seed)
    order = list(rng.permutation(len(scenarios)))
    folds: list[list[dict]] = [[] for _ in range(n_folds)]
    for position, scenario_index in enumerate(order):
        folds[position % n_folds].append(scenarios[int(scenario_index)])
    return folds


def mask_for_scenarios(events: pd.DataFrame, scenarios: list[dict]) -> pd.Series:
    mask = pd.Series(False, index=events.index)
    for scenario in scenarios:
        scenario_mask = pd.Series(True, index=events.index)
        for column, value in scenario.items():
            scenario_mask &= events[column] == value
        mask |= scenario_mask
    return mask


def fold_id_for_scenarios(scenarios: list[dict], fold_index: int) -> str:
    parts = [f"{item['site_id']}_{item['year']}_{item['variety']}" for item in scenarios]
    return f"fold{fold_index}:" + "|".join(parts)


def evaluate_grouped_cv_baseline(
    model: FittedPhenology,
    events: pd.DataFrame,
    weather_inputs: dict,
    folds: list[list[dict]],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    exact_frames = []
    major_frames = []
    for fold_index, scenarios in enumerate(folds, start=1):
        test = events[mask_for_scenarios(events, scenarios)].copy()
        fold_id = fold_id_for_scenarios(scenarios, fold_index)
        exact_frames.append(evaluate_exact(model, test, weather_inputs, "3fold", fold_id))
        major_frames.append(evaluate_major_first_dates(model, test, weather_inputs, "3fold", fold_id))
    return pd.concat(exact_frames, ignore_index=True), pd.concat(major_frames, ignore_index=True)


def run_grouped_cv(
    events: pd.DataFrame,
    weather_inputs: dict,
    prior_thresholds: dict[str, float],
    model_name: str,
    with_offsets: bool,
    offset_limit: float,
    maxiter: int,
    popsize: int,
    seed: int,
    folds: list[list[dict]],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    exact_frames = []
    major_frames = []
    fit_rows = []
    for fold_index, heldout_scenarios in enumerate(folds, start=1):
        test_mask = mask_for_scenarios(events, heldout_scenarios)
        train = events[~test_mask].copy()
        test = events[test_mask].copy()
        fold_id = fold_id_for_scenarios(heldout_scenarios, fold_index)
        model = fit_model(
            model_name,
            train,
            weather_inputs,
            prior_thresholds,
            with_offsets,
            offset_limit,
            maxiter,
            popsize,
            seed + fold_index,
        )
        exact_frames.append(evaluate_exact(model, test, weather_inputs, "3fold", fold_id))
        major_frames.append(evaluate_major_first_dates(model, test, weather_inputs, "3fold", fold_id))
        fit_rows.append(
            {
                "model": model_name,
                "fold_id": fold_id,
                "n_train_events": int(len(train)),
                "n_test_events": int(len(test)),
                **model.thermal_params.as_dict(),
                **{f"offset_{k}": v for k, v in model.cultivar_offsets.items()},
            }
        )
    return (
        pd.concat(exact_frames, ignore_index=True),
        pd.concat(major_frames, ignore_index=True),
        pd.DataFrame(fit_rows),
    )


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    events = load_first_observed_events(args.input)
    parameter_table = load_parameter_table(PHENO_DIR / "configs" / "BBCHGDD.json")
    prior_thresholds = platform_threshold_prior(events, parameter_table)
    weather_inputs = build_weather_inputs_for_events(events, args.cache_dir)
    folds = site_year_folds(events, args.n_folds, args.seed)

    events.to_csv(args.output_dir / "phenology_v2_first_observed_events.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(
        [{"BBCH_Principal": k, "prior_GDD": v} for k, v in sorted(prior_thresholds.items(), key=lambda item: int(item[0]))]
    ).to_csv(args.output_dir / "phenology_v2_prior_thresholds.csv", index=False, encoding="utf-8-sig")

    base = baseline_model(events, parameter_table)
    pooled = fit_model(
        "pooled_calibrated",
        events,
        weather_inputs,
        prior_thresholds,
        False,
        args.offset_limit,
        args.maxiter,
        args.popsize,
        args.seed,
    )
    cultivar = fit_model(
        "cultivar_offset_calibrated",
        events,
        weather_inputs,
        prior_thresholds,
        True,
        args.offset_limit,
        args.maxiter,
        args.popsize,
        args.seed + 100,
    )

    exact_resub = pd.concat(
        [
            evaluate_exact(base, events, weather_inputs, "resubstitution"),
            evaluate_exact(pooled, events, weather_inputs, "resubstitution"),
            evaluate_exact(cultivar, events, weather_inputs, "resubstitution"),
        ],
        ignore_index=True,
    )
    major_resub = pd.concat(
        [
            evaluate_major_first_dates(base, events, weather_inputs, "resubstitution"),
            evaluate_major_first_dates(pooled, events, weather_inputs, "resubstitution"),
            evaluate_major_first_dates(cultivar, events, weather_inputs, "resubstitution"),
        ],
        ignore_index=True,
    )

    pooled_exact_cv, pooled_major_cv, pooled_fits = run_grouped_cv(
        events,
        weather_inputs,
        prior_thresholds,
        "pooled_calibrated",
        False,
        args.offset_limit,
        args.maxiter,
        args.popsize,
        args.seed + 200,
        folds,
    )
    cultivar_exact_cv, cultivar_major_cv, cultivar_fits = run_grouped_cv(
        events,
        weather_inputs,
        prior_thresholds,
        "cultivar_offset_calibrated",
        True,
        args.offset_limit,
        args.maxiter,
        args.popsize,
        args.seed + 300,
        folds,
    )
    base_exact_cv, base_major_cv = evaluate_grouped_cv_baseline(base, events, weather_inputs, folds)

    exact = pd.concat([exact_resub, base_exact_cv, pooled_exact_cv, cultivar_exact_cv], ignore_index=True)
    major = pd.concat([major_resub, base_major_cv, pooled_major_cv, cultivar_major_cv], ignore_index=True)
    exact.to_csv(args.output_dir / "phenology_v2_exact_bbch_validation.csv", index=False, encoding="utf-8-sig")
    major.to_csv(args.output_dir / "phenology_v2_major_stage_validation.csv", index=False, encoding="utf-8-sig")
    pd.concat([pooled_fits, cultivar_fits], ignore_index=True).to_csv(
        args.output_dir / "phenology_v2_3fold_fitted_parameters.csv", index=False, encoding="utf-8-sig"
    )

    fitted_rows = []
    for model in [base, pooled, cultivar]:
        fitted_rows.append(
            {
                "model": model.model_name,
                **model.thermal_params.as_dict(),
                **{f"offset_{k}": v for k, v in model.cultivar_offsets.items()},
            }
        )
        pd.DataFrame(
            [
                {"model": model.model_name, "BBCH_Principal": stage, "GDD": value}
                for stage, value in sorted(model.thresholds.items(), key=lambda item: int(item[0]))
            ]
        ).to_csv(args.output_dir / f"phenology_v2_thresholds_{model.model_name}.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(fitted_rows).to_csv(args.output_dir / "phenology_v2_resub_fitted_parameters.csv", index=False, encoding="utf-8-sig")

    summary_rows = []
    for level, table in [("exact_bbch", exact), ("major_stage_first_date", major)]:
        for (model, evaluation), group in table.groupby(["model", "evaluation"]):
            summary_rows.append({"level": level, "model": model, "evaluation": evaluation, **metric_dict(group)})
    for (model, evaluation), group in exact.groupby(["model", "evaluation"]):
        valid = group.dropna(subset=["major_stage_match_on_observed_date"])
        summary_rows.append(
            {
                "level": "major_stage_state_on_observed_date",
                "model": model,
                "evaluation": evaluation,
                "n_events": int(len(valid)),
                "n_matched": int(len(valid)),
                "mae_days": math.nan,
                "rmse_days": math.nan,
                "bias_days": math.nan,
                "within_7_days": math.nan,
                "within_14_days": float(valid["major_stage_match_on_observed_date"].mean()) if len(valid) else math.nan,
            }
        )
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(args.output_dir / "phenology_v2_summary.csv", index=False, encoding="utf-8-sig")

    metadata = {
        "raw_file": str(args.input),
        "n_first_observed_events_excluding_bbch00": int(len(events)),
        "site_years": int(events[SCENARIO_COLUMNS].drop_duplicates().shape[0]),
        "observed_stages": sorted(events["BBCH_Principal"].unique(), key=lambda x: int(x)),
        "thermal_bounds": THERMAL_BOUNDS,
        "offset_limit_gdd": args.offset_limit,
        "prior_weight": PRIOR_WEIGHT,
        "cross_validation": {
            "method": "grouped_site_year_kfold",
            "n_folds": int(args.n_folds),
            "folds": [
                {
                    "fold_id": fold_id_for_scenarios(fold, index),
                    "site_years": [
                        {
                            "site_id": item["site_id"],
                            "year": int(item["year"]),
                            "variety": item["variety"],
                            "source_variety_code": events[
                                mask_for_scenarios(events, [item])
                            ]["source_variety_code"].iloc[0],
                        }
                        for item in fold
                    ],
                }
                for index, fold in enumerate(folds, start=1)
            ],
        },
        "variety_mapping": VARIETY_MAP,
    }
    (args.output_dir / "phenology_v2_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(summary.to_string(index=False))
    print(f"Wrote phenology v2 outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
