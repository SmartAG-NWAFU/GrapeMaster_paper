#!/usr/bin/env python3
"""Calibrate and validate the GrapeMaster standalone phenology module.

The script is intentionally conservative for the manuscript use case:
observed daily records are reduced to first-observed stage events, platform
thermal parameters are kept fixed, and validation is performed by
leave-one-site-year-out cross-validation.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PHENO_DIR = ROOT / "model_moudle" / "grape_bbch" / "standalone_phenology"
sys.path.insert(0, str(PHENO_DIR))

from evaluation import build_weather_inputs, scenario_key  # noqa: E402
from io_utils import SCENARIO_COLUMNS  # noqa: E402
from phenology_model import (  # noqa: E402
    ThermalParams,
    enforce_monotonic_thresholds,
    get_thresholds,
    load_parameter_table,
    resolve_parameter_key,
    save_parameter_table,
    simulate_phenology,
    update_parameter_thresholds,
)


VARIETY_MAP = {
    "wk": {"variety": "温克", "maturation": "晚"},
    "JF": {"variety": "巨峰", "maturation": "中"},
    "MPT": {"variety": "毛葡萄野酿2号", "maturation": "晚"},
}

MANAGEMENT_STAGE_LABELS = {
    "inflorescence_flowering": "Inflorescence and flowering",
    "berry_development": "Berry development",
    "ripening": "Ripening",
}


@dataclass(frozen=True)
class MetricSummary:
    n_events: int
    n_matched: int
    mae_days: float
    rmse_days: float
    bias_days: float
    within_7_days: float

    def as_dict(self) -> dict:
        return {
            "n_events": self.n_events,
            "n_matched": self.n_matched,
            "mae_days": self.mae_days,
            "rmse_days": self.rmse_days,
            "bias_days": self.bias_days,
            "within_7_days": self.within_7_days,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Conservative phenology calibration and validation for GrapeMaster."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=PHENO_DIR / "data" / "growth_stage_data.xlsx",
        help="Excel file with raw phenology observations.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "phenology",
        help="Directory for validation outputs.",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=ROOT / "results" / "phenology" / "weather_cache",
        help="Weather cache directory.",
    )
    parser.add_argument(
        "--min-stage-events",
        type=int,
        default=2,
        help="Minimum training events required to update a BBCH threshold.",
    )
    return parser.parse_args()


def management_stage(bbch: str) -> str | None:
    value = int(str(bbch).zfill(2))
    if 50 <= value <= 69:
        return "inflorescence_flowering"
    if 70 <= value <= 79:
        return "berry_development"
    if 80 <= value <= 89:
        return "ripening"
    return None


def load_raw_events(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raw = pd.read_excel(path)
    raw["date"] = pd.to_datetime(raw["date"])
    raw["year"] = raw["date"].dt.year.astype(int)
    observed = raw.dropna(subset=["growth_stage"]).copy()
    observed["BBCH_Principal"] = observed["growth_stage"].astype(int).astype(str).str.zfill(2)

    mapped_rows = []
    for _, row in observed.iterrows():
        code = str(row["variety"])
        if code not in VARIETY_MAP:
            raise ValueError(f"Unsupported variety code: {code}")
        mapped = VARIETY_MAP[code]
        mapped_rows.append(
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
                "observed_date": row["date"].strftime("%Y-%m-%d"),
                "management_stage": management_stage(row["BBCH_Principal"]),
            }
        )

    event_rows = pd.DataFrame(mapped_rows)
    exact_events = (
        event_rows.sort_values("observed_date")
        .drop_duplicates(SCENARIO_COLUMNS + ["BBCH_Principal"], keep="first")
        .reset_index(drop=True)
    )
    grouped_events = (
        event_rows.dropna(subset=["management_stage"])
        .sort_values("observed_date")
        .drop_duplicates(SCENARIO_COLUMNS + ["management_stage"], keep="first")
        .reset_index(drop=True)
    )
    return event_rows, exact_events, grouped_events


def scenario_records(observations: pd.DataFrame) -> list[dict]:
    return observations[SCENARIO_COLUMNS].drop_duplicates().to_dict(orient="records")


def build_weather_inputs_for_events(events: pd.DataFrame, cache_dir: Path) -> dict:
    obs = events[SCENARIO_COLUMNS + ["BBCH_Principal", "observed_date"]].copy()
    return build_weather_inputs(obs, cache_dir)


def supported_exact_events(events: pd.DataFrame, parameter_table: dict) -> pd.DataFrame:
    rows = []
    for scenario in scenario_records(events):
        scenario_events = events.copy()
        for column, value in scenario.items():
            scenario_events = scenario_events[scenario_events[column] == value]
        supported = set(
            get_thresholds(
                scenario["province"],
                scenario["variety"],
                scenario["maturation"],
                parameter_table=parameter_table,
            )["GS"].astype(str).str.zfill(2)
        )
        scenario_events = scenario_events[
            scenario_events["BBCH_Principal"].astype(str).str.zfill(2).isin(supported)
        ].copy()
        scenario_events = scenario_events[scenario_events["BBCH_Principal"].astype(str).str.zfill(2) != "00"]
        rows.append(scenario_events)
    return pd.concat(rows, ignore_index=True) if rows else events.iloc[0:0].copy()


def simulation_for_scenario(
    scenario: dict,
    weather_inputs: dict,
    parameter_table: dict,
    thermal_params: ThermalParams = ThermalParams(),
) -> pd.DataFrame:
    return simulate_phenology(
        daily_weather=weather_inputs[scenario_key(scenario)],
        year=int(scenario["year"]),
        province=scenario["province"],
        variety=scenario["variety"],
        maturation=scenario["maturation"],
        thermal_params=thermal_params,
        parameter_table=parameter_table,
    )


def threshold_midpoints_on_observed_dates(
    simulation: pd.DataFrame, observations: pd.DataFrame
) -> pd.DataFrame:
    sim = simulation[["Date", "GDDCUSUM"]].copy()
    sim["previous_GDDCUSUM"] = sim["GDDCUSUM"].shift(1).fillna(0.0)
    sim["Date"] = pd.to_datetime(sim["Date"]).dt.strftime("%Y-%m-%d")
    obs = observations.copy()
    obs["observed_date"] = pd.to_datetime(obs["observed_date"]).dt.strftime("%Y-%m-%d")
    merged = obs.merge(sim, left_on="observed_date", right_on="Date", how="left")
    merged["threshold_candidate"] = (
        merged["previous_GDDCUSUM"].astype(float) + merged["GDDCUSUM"].astype(float)
    ) / 2.0
    return merged.drop(columns=["Date"])


def calibrate_thresholds_conservative(
    train_events: pd.DataFrame,
    weather_inputs: dict,
    original_parameters: dict,
    min_stage_events: int,
) -> dict:
    calibrated = json.loads(json.dumps(original_parameters, ensure_ascii=False))
    updates_by_key: dict[tuple[str, str], list[pd.DataFrame]] = {}

    for scenario in scenario_records(train_events):
        scenario_events = train_events.copy()
        for column, value in scenario.items():
            scenario_events = scenario_events[scenario_events[column] == value]
        simulation = simulation_for_scenario(scenario, weather_inputs, calibrated)
        thresholds = get_thresholds(
            scenario["province"],
            scenario["variety"],
            scenario["maturation"],
            parameter_table=calibrated,
        )
        supported = set(thresholds["GS"].astype(str).str.zfill(2))
        scenario_events = scenario_events[scenario_events["BBCH_Principal"].isin(supported)].copy()
        scenario_events = scenario_events[scenario_events["BBCH_Principal"] != "00"].copy()
        if scenario_events.empty:
            continue
        midpoint_table = threshold_midpoints_on_observed_dates(simulation, scenario_events)
        parameter_key = (
            scenario["province"],
            resolve_parameter_key(
                scenario["province"],
                scenario["variety"],
                scenario["maturation"],
                calibrated,
            ),
        )
        updates_by_key.setdefault(parameter_key, []).append(midpoint_table)

    for (province, parameter_name), frames in updates_by_key.items():
        observed_gdd = pd.concat(frames, ignore_index=True).dropna(subset=["threshold_candidate"])
        if observed_gdd.empty:
            continue
        thresholds = get_thresholds(province, parameter_name, parameter_name, parameter_table=calibrated)
        for stage, group in observed_gdd.groupby("BBCH_Principal"):
            stage = str(stage).zfill(2)
            if len(group) < min_stage_events:
                continue
            mask = thresholds["GS"].astype(str).str.zfill(2) == stage
            if mask.any():
                thresholds.loc[mask, "GDD"] = float(group["threshold_candidate"].median())
        thresholds = enforce_monotonic_thresholds(thresholds)
        calibrated = update_parameter_thresholds(
            calibrated,
            province,
            parameter_name,
            parameter_name,
            thresholds,
        )
    return calibrated


def first_dates_by_stage(simulation: pd.DataFrame) -> dict[str, str]:
    dates = {}
    for _, row in simulation.iterrows():
        dates.setdefault(str(row["BBCH_Principal"]).zfill(2), row["Date"])
    return dates


def first_dates_by_management_stage(simulation: pd.DataFrame) -> dict[str, str]:
    dates = {}
    for _, row in simulation.iterrows():
        stage = management_stage(str(row["BBCH_Principal"]).zfill(2))
        if stage is not None:
            dates.setdefault(stage, row["Date"])
    return dates


def evaluate_exact_events(events: pd.DataFrame, weather_inputs: dict, parameter_table: dict, label: str) -> pd.DataFrame:
    rows = []
    for scenario in scenario_records(events):
        scenario_events = events.copy()
        for column, value in scenario.items():
            scenario_events = scenario_events[scenario_events[column] == value]
        simulation = simulation_for_scenario(scenario, weather_inputs, parameter_table)
        predicted_dates = first_dates_by_stage(simulation)
        supported = set(
            get_thresholds(
                scenario["province"], scenario["variety"], scenario["maturation"], parameter_table=parameter_table
            )["GS"].astype(str).str.zfill(2)
        )
        for _, event in scenario_events.iterrows():
            stage = str(event["BBCH_Principal"]).zfill(2)
            if stage not in supported:
                predicted = None
            else:
                predicted = predicted_dates.get(stage)
            error = None if predicted is None else (pd.to_datetime(predicted) - pd.to_datetime(event["observed_date"])).days
            rows.append(
                {
                    "evaluation": label,
                    **{column: event[column] for column in SCENARIO_COLUMNS},
                    "source_variety_code": event["source_variety_code"],
                    "BBCH_Principal": stage,
                    "observed_date": event["observed_date"],
                    "predicted_date": predicted,
                    "error_days": error,
                    "abs_error_days": abs(error) if error is not None else None,
                    "matched": predicted is not None,
                }
            )
    return pd.DataFrame(rows)


def evaluate_grouped_events(
    grouped_events: pd.DataFrame, weather_inputs: dict, parameter_table: dict, label: str
) -> pd.DataFrame:
    rows = []
    for scenario in scenario_records(grouped_events):
        scenario_events = grouped_events.copy()
        for column, value in scenario.items():
            scenario_events = scenario_events[scenario_events[column] == value]
        simulation = simulation_for_scenario(scenario, weather_inputs, parameter_table)
        predicted_dates = first_dates_by_management_stage(simulation)
        for _, event in scenario_events.iterrows():
            group = event["management_stage"]
            predicted = predicted_dates.get(group)
            error = None if predicted is None else (pd.to_datetime(predicted) - pd.to_datetime(event["observed_date"])).days
            rows.append(
                {
                    "evaluation": label,
                    **{column: event[column] for column in SCENARIO_COLUMNS},
                    "source_variety_code": event["source_variety_code"],
                    "management_stage": group,
                    "management_stage_label": MANAGEMENT_STAGE_LABELS[group],
                    "observed_date": event["observed_date"],
                    "predicted_date": predicted,
                    "error_days": error,
                    "abs_error_days": abs(error) if error is not None else None,
                    "matched": predicted is not None,
                }
            )
    return pd.DataFrame(rows)


def summarize_metrics(table: pd.DataFrame) -> MetricSummary:
    matched = table.dropna(subset=["abs_error_days"]).copy()
    if matched.empty:
        return MetricSummary(len(table), 0, math.nan, math.nan, math.nan, math.nan)
    errors = matched["error_days"].astype(float)
    abs_errors = matched["abs_error_days"].astype(float)
    return MetricSummary(
        n_events=int(len(table)),
        n_matched=int(len(matched)),
        mae_days=float(abs_errors.mean()),
        rmse_days=float((errors.pow(2).mean()) ** 0.5),
        bias_days=float(errors.mean()),
        within_7_days=float((abs_errors <= 7).mean()),
    )


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    all_observations, exact_events, grouped_events = load_raw_events(args.input)
    exact_events.to_csv(args.output_dir / "phenology_first_observed_bbch_events.csv", index=False, encoding="utf-8-sig")
    grouped_events.to_csv(
        args.output_dir / "phenology_first_observed_management_stage_events.csv",
        index=False,
        encoding="utf-8-sig",
    )

    weather_inputs = build_weather_inputs_for_events(exact_events, args.cache_dir)
    original_parameters = load_parameter_table(PHENO_DIR / "configs" / "BBCHGDD.json")
    exact_metric_events = supported_exact_events(exact_events, original_parameters)
    exact_metric_events.to_csv(
        args.output_dir / "phenology_supported_bbch_transition_events.csv",
        index=False,
        encoding="utf-8-sig",
    )
    calibrated_all = calibrate_thresholds_conservative(
        exact_metric_events, weather_inputs, original_parameters, args.min_stage_events
    )
    save_parameter_table(calibrated_all, args.output_dir / "calibrated_BBCHGDD_conservative.json")

    exact_baseline = evaluate_exact_events(exact_metric_events, weather_inputs, original_parameters, "baseline")
    exact_calibrated_resub = evaluate_exact_events(
        exact_metric_events, weather_inputs, calibrated_all, "calibrated_resubstitution"
    )
    grouped_baseline = evaluate_grouped_events(grouped_events, weather_inputs, original_parameters, "baseline")
    grouped_calibrated_resub = evaluate_grouped_events(
        grouped_events, weather_inputs, calibrated_all, "calibrated_resubstitution"
    )

    exact_losyo_frames = []
    grouped_losyo_frames = []
    for heldout in scenario_records(exact_metric_events):
        mask = pd.Series(True, index=exact_metric_events.index)
        for column, value in heldout.items():
            mask &= exact_metric_events[column] == value
        train = exact_metric_events[~mask].copy()
        test_exact = exact_metric_events[mask].copy()

        grouped_mask = pd.Series(True, index=grouped_events.index)
        for column, value in heldout.items():
            grouped_mask &= grouped_events[column] == value
        test_grouped = grouped_events[grouped_mask].copy()

        fold_parameters = calibrate_thresholds_conservative(
            train, weather_inputs, original_parameters, args.min_stage_events
        )
        fold_id = f"{heldout['site_id']}_{heldout['year']}_{heldout['variety']}"
        exact_fold = evaluate_exact_events(test_exact, weather_inputs, fold_parameters, "losyo_calibrated")
        exact_fold["fold_id"] = fold_id
        grouped_fold = evaluate_grouped_events(test_grouped, weather_inputs, fold_parameters, "losyo_calibrated")
        grouped_fold["fold_id"] = fold_id
        exact_losyo_frames.append(exact_fold)
        grouped_losyo_frames.append(grouped_fold)

    exact_losyo = pd.concat(exact_losyo_frames, ignore_index=True)
    grouped_losyo = pd.concat(grouped_losyo_frames, ignore_index=True)

    exact_eval = pd.concat([exact_baseline, exact_calibrated_resub, exact_losyo], ignore_index=True)
    grouped_eval = pd.concat([grouped_baseline, grouped_calibrated_resub, grouped_losyo], ignore_index=True)
    exact_eval.to_csv(args.output_dir / "phenology_exact_event_validation.csv", index=False, encoding="utf-8-sig")
    grouped_eval.to_csv(args.output_dir / "phenology_management_stage_validation.csv", index=False, encoding="utf-8-sig")

    summary_rows = []
    for level, table in [("exact_bbch_event", exact_eval), ("management_stage", grouped_eval)]:
        for evaluation, group in table.groupby("evaluation"):
            summary = summarize_metrics(group).as_dict()
            summary_rows.append({"level": level, "evaluation": evaluation, **summary})
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(args.output_dir / "phenology_validation_summary.csv", index=False, encoding="utf-8-sig")

    metadata = {
        "raw_rows": int(len(pd.read_excel(args.input))),
        "valid_observations": int(len(all_observations)),
        "site_years": int(exact_events[SCENARIO_COLUMNS].drop_duplicates().shape[0]),
        "exact_first_observed_events": int(len(exact_events)),
        "supported_bbch_transition_events": int(len(exact_metric_events)),
        "management_stage_events": int(len(grouped_events)),
        "thermal_params": ThermalParams().as_dict(),
        "min_stage_events_for_threshold_update": args.min_stage_events,
        "variety_mapping": VARIETY_MAP,
    }
    (args.output_dir / "phenology_validation_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(summary.to_string(index=False))
    print(f"Wrote phenology validation outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
