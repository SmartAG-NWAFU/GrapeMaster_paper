#!/usr/bin/env python3
"""Build an audit table for a representative GrapeMaster crop-season replay."""

from __future__ import annotations

import json
import ast
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "dataset_csv"
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)

REPRESENTATIVE_CROP_UUID = "62f4173f-0c6f-44a6-9629-11e205def74b"
PHENOLOGY_STAGE_LABELS = {
    "萌芽期": "budburst",
    "展叶期": "leaf expansion",
    "花序期": "inflorescence development",
    "开花期": "flowering",
    "坐果期": "fruit set",
    "果实膨大期": "berry enlargement",
    "转色期": "veraison",
    "成熟期": "ripening",
}


def read_csv(name: str) -> pd.DataFrame:
    path = DATA / name
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except Exception:
        return pd.DataFrame()


def compact_uuid(value: str) -> str:
    value = str(value)
    return f"{value[:8]}...{value[-4:]}" if len(value) > 16 else value


def count_by_uuid(df: pd.DataFrame, column: str, uuid: str) -> int:
    if df.empty or column not in df.columns:
        return 0
    return int((df[column].astype(str) == uuid).sum())


def load_tables() -> dict[str, pd.DataFrame]:
    return {
        "crop": read_csv("public_crop_cropseason.csv"),
        "weather": read_csv("public_weatherdata_cropweather.csv"),
        "phenology": read_csv("public_phendata_phendata.csv"),
        "risk": read_csv("public_diseasedata_diseasedata.csv"),
        "notifications": read_csv("public_notice_notification.csv"),
        "tasks": read_csv("public_task_cropprotection.csv"),
        "fungicides": read_csv("public_task_fungicides.csv"),
        "notes": read_csv("public_note_recode.csv"),
        "incidence_notes": read_csv("public_note_incidencenote.csv"),
    }


def build_candidate_scores(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    crop = tables["crop"]
    tasks = tables["tasks"]
    fungicides = tables["fungicides"]
    notes = tables["notes"]
    incidence = tables["incidence_notes"]

    if not fungicides.empty and not tasks.empty:
        fung_task = fungicides.merge(
            tasks[["uuid", "crop_uuid_id", "execution_time", "task_status"]],
            left_on="task_id",
            right_on="uuid",
            how="left",
        )
    else:
        fung_task = pd.DataFrame()

    if not incidence.empty and not notes.empty:
        incidence_joined = incidence.merge(
            notes[["uuid", "crop_uuid_id", "created_datetime", "type"]],
            left_on="recode_ptr_id",
            right_on="uuid",
            how="left",
        )
    else:
        incidence_joined = pd.DataFrame()

    rows = []
    for _, row in crop.iterrows():
        uuid = str(row["uuid"])
        task_rows = tasks[tasks.get("crop_uuid_id", pd.Series(dtype=str)).astype(str) == uuid]
        statuses = task_rows.get("task_status", pd.Series(dtype=str)).astype(str)
        result = {
            "crop_uuid": uuid,
            "field_name": row.get("field_name", ""),
            "variety": row.get("grape_variety", ""),
            "weather_records": count_by_uuid(tables["weather"], "cropseason_uuid_id", uuid),
            "phenology_records": count_by_uuid(tables["phenology"], "crop_uuid_id", uuid),
            "risk_records": count_by_uuid(tables["risk"], "crop_uuid_id", uuid),
            "notification_records": count_by_uuid(tables["notifications"], "crop_uuid_id", uuid),
            "task_records": len(task_rows),
            "completed_task_records": int(statuses.str.contains("完成|completed", case=False, na=False).sum()),
            "fungicide_records": count_by_uuid(fung_task, "crop_uuid_id", uuid),
            "note_records": count_by_uuid(notes, "crop_uuid_id", uuid),
            "incidence_note_records": count_by_uuid(incidence_joined, "crop_uuid_id", uuid),
        }
        result["coverage_score"] = sum(
            result[key] > 0
            for key in [
                "weather_records",
                "phenology_records",
                "risk_records",
                "notification_records",
                "task_records",
                "fungicide_records",
                "note_records",
                "incidence_note_records",
            ]
        )
        rows.append(result)

    return pd.DataFrame(rows).sort_values(
        [
            "coverage_score",
            "notification_records",
            "task_records",
            "fungicide_records",
            "incidence_note_records",
        ],
        ascending=False,
    )


def parse_json_cell(value: object) -> dict:
    if pd.isna(value):
        return {}
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return {}


def extract_json_list(value: object, key: str) -> list:
    """Extract a top-level JSON list from long exported strings that may be truncated."""
    text = "" if pd.isna(value) else str(value)
    parsed = parse_json_cell(text)
    if key in parsed and isinstance(parsed[key], list):
        return parsed[key]
    match = re.search(r'"' + re.escape(key) + r'"\s*:\s*(\[.*?\])', text)
    if not match:
        return []
    try:
        extracted = ast.literal_eval(match.group(1))
    except (SyntaxError, ValueError):
        return []
    return extracted if isinstance(extracted, list) else []


def summarize_sequence(values: list) -> str:
    if not values:
        return "No sequence"
    counts = pd.Series(values).astype(str).value_counts().to_dict()
    return "; ".join(f"{key}: {value}" for key, value in counts.items())


def build_replay_table(tables: dict[str, pd.DataFrame], uuid: str) -> pd.DataFrame:
    crop = tables["crop"]
    weather = tables["weather"]
    phenology = tables["phenology"]
    risk = tables["risk"]
    notifications = tables["notifications"]
    tasks = tables["tasks"]
    fungicides = tables["fungicides"]
    notes = tables["notes"]
    incidence = tables["incidence_notes"]

    crop_row = crop[crop["uuid"].astype(str) == uuid].iloc[0]

    weather_rows = weather[weather.get("cropseason_uuid_id", pd.Series(dtype=str)).astype(str) == uuid]
    phen_rows = phenology[phenology.get("crop_uuid_id", pd.Series(dtype=str)).astype(str) == uuid]
    risk_rows = risk[risk.get("crop_uuid_id", pd.Series(dtype=str)).astype(str) == uuid]
    notification_rows = notifications[
        notifications.get("crop_uuid_id", pd.Series(dtype=str)).astype(str) == uuid
    ]
    task_rows = tasks[tasks.get("crop_uuid_id", pd.Series(dtype=str)).astype(str) == uuid]

    if not fungicides.empty and not task_rows.empty:
        fung_task = fungicides.merge(
            task_rows[["uuid", "crop_uuid_id", "execution_time", "task_status"]],
            left_on="task_id",
            right_on="uuid",
            how="inner",
        )
    else:
        fung_task = pd.DataFrame()

    if not incidence.empty and not notes.empty:
        incidence_joined = incidence.merge(
            notes[["uuid", "crop_uuid_id", "created_datetime", "type"]],
            left_on="recode_ptr_id",
            right_on="uuid",
            how="left",
        )
        incidence_rows = incidence_joined[incidence_joined.get("crop_uuid_id", pd.Series(dtype=str)).astype(str) == uuid]
    else:
        incidence_rows = pd.DataFrame()

    phen_obj = parse_json_cell(phen_rows.iloc[0]["phendata"]) if len(phen_rows) else {}
    weather_daily = parse_json_cell(weather_rows.iloc[0]["daily"]) if len(weather_rows) else {}

    risk_text = risk_rows.iloc[0]["diseasedata"] if len(risk_rows) else ""
    risk_dates = extract_json_list(risk_text, "Date")
    field_risk = extract_json_list(risk_text, "FieldRiskCode")
    actions = extract_json_list(risk_text, "actionTypeCode")
    risk_summary = summarize_sequence(field_risk)
    action_summary = summarize_sequence(actions)
    phen_stages_raw = pd.Series(phen_obj.get("principal_code", [])).dropna().astype(str).unique().tolist()
    phen_stages = [PHENOLOGY_STAGE_LABELS.get(stage, stage) for stage in phen_stages_raw]
    weather_dates = weather_daily.get("time", [])

    disease_notifications = notification_rows[
        notification_rows["title"].astype(str).str.contains("风险|打药", na=False)
        | notification_rows["text"].astype(str).str.contains("霜霉病|白粉病|病害防治|高风险", na=False)
    ]

    completed_tasks = task_rows[
        task_rows.get("task_status", pd.Series(dtype=str)).astype(str).str.contains("完成|completed", case=False, na=False)
    ]

    replay_rows = [
        {
            "workflow_step": "Field and crop-season anchor",
            "source_table": "public_crop_cropseason",
            "observed_record": (
                f"Crop-season {compact_uuid(uuid)}; Du'an Kangsheng wild-grape field, "
                f"open-field cultivation, {crop_row.get('field_size', '')} m2."
            ),
            "closed_loop_role": "Defines the field-season object used to link weather, risk, notifications, and tasks.",
        },
        {
            "workflow_step": "Weather update",
            "source_table": "public_weatherdata_cropweather",
            "observed_record": (
                f"{len(weather_rows)} weather payload; daily forecast span "
                f"{weather_dates[0] if weather_dates else 'NA'} to {weather_dates[-1] if weather_dates else 'NA'}."
            ),
            "closed_loop_role": "Provides environmental input for crop-season state and risk interpretation.",
        },
        {
            "workflow_step": "Phenology state",
            "source_table": "public_phendata_phendata",
            "observed_record": (
                f"{len(phen_rows)} phenology payload; principal stages include "
                f"{', '.join(phen_stages[:4])}{'...' if len(phen_stages) > 4 else ''}."
            ),
            "closed_loop_role": "Adds crop-stage context for risk windows and operation timing.",
        },
        {
            "workflow_step": "Disease-risk timeline",
            "source_table": "public_diseasedata_diseasedata",
            "observed_record": (
                f"{len(risk_rows)} risk payload covering "
                f"{risk_dates[0] if risk_dates else 'NA'} to {risk_dates[-1] if risk_dates else 'NA'}; "
                f"risk states: {risk_summary}; action states: {action_summary}."
            ),
            "closed_loop_role": "Transforms model output into a date-indexed field-risk and action sequence.",
        },
        {
            "workflow_step": "Risk and event delivery",
            "source_table": "public_notice_notification",
            "observed_record": (
                f"{len(notification_rows)} notifications; {len(disease_notifications)} disease-risk or spray-reminder notifications; "
                f"{int(notification_rows.get('read', pd.Series(dtype=bool)).fillna(False).sum())} marked as read."
            ),
            "closed_loop_role": "Delivers risk and crop-season events as reviewable records linked to the same crop season.",
        },
        {
            "workflow_step": "Plant-protection task execution",
            "source_table": "public_task_cropprotection",
            "observed_record": (
                f"{len(task_rows)} plant-protection tasks; {len(completed_tasks)} completed; execution dates: "
                f"{', '.join(task_rows.get('execution_time', pd.Series(dtype=str)).dropna().astype(str).tolist())}."
            ),
            "closed_loop_role": "Converts reviewed risk or management events into executable field-operation records.",
        },
        {
            "workflow_step": "Fungicide management feedback",
            "source_table": "public_task_fungicides",
            "observed_record": (
                f"{len(fung_task)} fungicide-product entries linked to the completed plant-protection tasks."
            ),
            "closed_loop_role": "Supplies structured treatment feedback for protection-state updating and later review.",
        },
        {
            "workflow_step": "Symptom or field-evidence archive",
            "source_table": "public_note_recode / public_note_incidencenote",
            "observed_record": (
                f"{count_by_uuid(notes, 'crop_uuid_id', uuid)} field-note records and "
                f"{len(incidence_rows)} incidence-note records linked to this crop season."
            ),
            "closed_loop_role": "Documents whether post-operation field evidence is available for the same crop-season record chain.",
        },
    ]
    return pd.DataFrame(replay_rows)


def main() -> None:
    tables = load_tables()
    candidates = build_candidate_scores(tables)
    candidates.to_csv(OUT / "crop_season_replay_candidate_scores.csv", index=False)

    replay = build_replay_table(tables, REPRESENTATIVE_CROP_UUID)
    replay.to_csv(OUT / "crop_season_replay_audit.csv", index=False)

    meta = {
        "representative_crop_uuid": REPRESENTATIVE_CROP_UUID,
        "candidate_scores_path": str(OUT / "crop_season_replay_candidate_scores.csv"),
        "audit_table_path": str(OUT / "crop_season_replay_audit.csv"),
    }
    (OUT / "crop_season_replay_audit_summary.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
