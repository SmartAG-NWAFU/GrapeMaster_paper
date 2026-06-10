#!/usr/bin/env python3
"""Summarize operational backend record coverage for GrapeMaster.

The script reports cleaned, account-screened backend coverage. It excludes
registered accounts that do not have both field and crop-season records, then
counts only records linked to the retained accounts, retained fields, retained
crop seasons, or downstream retained task records.
"""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "dataset_csv"
OUT_DIR = ROOT / "results"


def read_csv(name: str) -> list[dict[str, str]]:
    path = DATA_DIR / name
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def nonempty(value: str | None) -> bool:
    return bool(value and str(value).strip())


def unique_nonempty(rows: list[dict[str, str]], field: str) -> set[str]:
    return {row[field].strip() for row in rows if nonempty(row.get(field))}


def count_if(rows: list[dict[str, str]], predicate) -> int:
    return sum(1 for row in rows if predicate(row))


def date_range(rows: list[dict[str, str]], fields: tuple[str, ...]) -> str:
    dates: list[str] = []
    for row in rows:
        for field in fields:
            value = row.get(field, "")
            if value:
                dates.append(value[:10])
    if not dates:
        return ""
    return f"{min(dates)} to {max(dates)}"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    auth_users = read_csv("public_auth_user.csv")
    users = read_csv("public_user_customuser.csv")
    fields = read_csv("public_field_field.csv")
    cropseasons = read_csv("public_crop_cropseason.csv")
    weather = read_csv("public_weatherdata_cropweather.csv")
    phenology = read_csv("public_phendata_phendata.csv")
    disease = read_csv("public_diseasedata_diseasedata.csv")
    disease_rb = read_csv("public_diseasedata_rb.csv")
    notifications = read_csv("public_notice_notification.csv")
    crop_tasks = read_csv("public_task_cropprotection.csv")
    irrigation_tasks = read_csv("public_task_irrigation.csv")
    fungicides = read_csv("public_task_fungicides.csv")
    pesticides = read_csv("public_task_pesticides.csv")
    notes = read_csv("public_note_recode.csv")
    growth_notes = read_csv("public_note_growthstagenote.csv")
    incidence_notes = read_csv("public_note_incidencenote.csv")
    disease_reports = read_csv("public_warn_discoveringdiseases.csv")
    advisory_sessions = read_csv("public_jiaojia_jiaojia.csv")
    messages = read_csv("public_message_message.csv")
    advisory_messages = read_csv("public_message_jiaojiamessage.csv")
    vit_images = read_csv("public_vitgpt_image.csv")
    vit_records = read_csv("public_vitgpt_vit.csv")
    segmentation_uploads = read_csv("public_seg_imageupload.csv")
    yolo_images = read_csv("public_yolo_image.csv")
    yolo_records = read_csv("public_yolo_yolo_m.csv")
    suggestions = read_csv("public_suggestions_suggestion.csv")
    forum_posts = read_csv("public_forum_forumpost.csv")
    forum_comments = read_csv("public_forum_comment.csv")
    forum_replies = read_csv("public_forum_reply.csv")

    raw_user_ids = unique_nonempty(auth_users, "id") | unique_nonempty(users, "user_id")
    phone_by_user_id = {
        row.get("user_id", "").strip(): row.get("phone", "").strip()
        for row in users
        if nonempty(row.get("user_id")) and nonempty(row.get("phone"))
    }
    for row in auth_users:
        user_id = row.get("id", "").strip()
        username = row.get("username", "").strip()
        if user_id and username and user_id not in phone_by_user_id:
            phone_by_user_id[user_id] = username

    fields_by_phone = Counter(row.get("user_id_id", "").strip() for row in fields if nonempty(row.get("user_id_id")))
    field_uuid_to_phone = {
        row.get("uuid", "").strip(): row.get("user_id_id", "").strip()
        for row in fields
        if nonempty(row.get("uuid")) and nonempty(row.get("user_id_id"))
    }

    cropseason_by_phone: Counter[str] = Counter()
    cropseason_uuid_to_phone: dict[str, str] = {}
    cropseason_uuid_to_field: dict[str, str] = {}
    for row in cropseasons:
        crop_uuid = row.get("uuid", "").strip()
        field_uuid = row.get("field_uuid_id", "").strip()
        phone = field_uuid_to_phone.get(field_uuid, "")
        if crop_uuid and phone:
            cropseason_by_phone[phone] += 1
            cropseason_uuid_to_phone[crop_uuid] = phone
            cropseason_uuid_to_field[crop_uuid] = field_uuid

    active_user_ids: set[str] = set()
    active_phones: set[str] = set()
    for user_id, phone in phone_by_user_id.items():
        if fields_by_phone.get(phone, 0) > 0 and cropseason_by_phone.get(phone, 0) > 0:
            active_user_ids.add(user_id)
            active_phones.add(phone)

    active_field_uuids = {
        row.get("uuid", "").strip()
        for row in fields
        if row.get("user_id_id", "").strip() in active_phones and nonempty(row.get("uuid"))
    }
    active_cropseason_uuids = {
        row.get("uuid", "").strip()
        for row in cropseasons
        if row.get("uuid", "").strip() in cropseason_uuid_to_phone
        and cropseason_uuid_to_phone[row.get("uuid", "").strip()] in active_phones
    }
    active_crop_task_uuids = {
        row.get("uuid", "").strip()
        for row in crop_tasks
        if row.get("crop_uuid_id", "").strip() in active_cropseason_uuids and nonempty(row.get("uuid"))
    }
    active_irrigation_task_uuids = {
        row.get("uuid", "").strip()
        for row in irrigation_tasks
        if row.get("crop_uuid_id", "").strip() in active_cropseason_uuids and nonempty(row.get("uuid"))
    }

    def linked_by_phone(row: dict[str, str]) -> bool:
        return row.get("user_id_id", "").strip() in active_phones

    def linked_by_crop(row: dict[str, str], key: str = "crop_uuid_id") -> bool:
        return row.get(key, "").strip() in active_cropseason_uuids

    active_field_rows = [row for row in fields if row.get("uuid", "").strip() in active_field_uuids]
    active_cropseason_rows = [row for row in cropseasons if row.get("uuid", "").strip() in active_cropseason_uuids]
    active_weather_rows = [row for row in weather if linked_by_crop(row, "cropseason_uuid_id")]
    active_phenology_rows = [row for row in phenology if linked_by_crop(row, "crop_uuid_id")]
    active_disease_rows = [row for row in disease if linked_by_crop(row, "crop_uuid_id")]
    active_disease_rb_rows = [row for row in disease_rb if linked_by_crop(row, "crop_uuid_id")]
    active_notification_rows = [
        row
        for row in notifications
        if row.get("user_id_id", "").strip() in active_phones
        or row.get("crop_uuid_id", "").strip() in active_cropseason_uuids
    ]
    active_crop_task_rows = [row for row in crop_tasks if linked_by_crop(row)]
    active_irrigation_task_rows = [row for row in irrigation_tasks if linked_by_crop(row)]
    active_fungicide_rows = [row for row in fungicides if row.get("task_id", "").strip() in active_crop_task_uuids]
    active_pesticide_rows = [row for row in pesticides if row.get("task_id", "").strip() in active_crop_task_uuids]
    active_note_rows = [row for row in notes if linked_by_crop(row)]
    active_disease_report_rows = [
        row
        for row in disease_reports
        if row.get("user_id_id", "").strip() in active_phones
        or row.get("field_id_id", "").strip() in active_field_uuids
    ]
    active_advisory_session_rows = [row for row in advisory_sessions if linked_by_phone(row)]
    active_message_rows = [row for row in messages if linked_by_phone(row)]
    active_advisory_message_rows = [row for row in advisory_messages if linked_by_phone(row)]
    active_vit_rows = [row for row in vit_records if linked_by_phone(row)]
    active_forum_rows = [row for row in forum_posts + forum_comments + forum_replies if linked_by_phone(row)]
    active_suggestion_rows = [row for row in suggestions if row.get("user_name", "").strip() in active_phones]

    total_notes = len(active_note_rows) + len(growth_notes) + len(incidence_notes)
    total_image_records = len(active_vit_rows) + len(segmentation_uploads) + len(yolo_records)
    total_advisory_records = len(active_advisory_session_rows) + len(active_message_rows) + len(active_advisory_message_rows) + len(active_suggestion_rows)
    total_task_records = len(active_crop_task_rows) + len(active_irrigation_task_rows)

    retained_account_rows = []
    for user_id in sorted(active_user_ids, key=lambda x: int(x) if x.isdigit() else x):
        phone = phone_by_user_id[user_id]
        retained_account_rows.append(
            {
                "user_id": user_id,
                "account": phone,
                "fields": fields_by_phone.get(phone, 0),
                "crop_seasons": cropseason_by_phone.get(phone, 0),
                "notifications": count_if(active_notification_rows, lambda row, phone=phone: row.get("user_id_id", "").strip() == phone),
                "crop_protection_tasks": count_if(active_crop_task_rows, lambda row, phone=phone: cropseason_uuid_to_phone.get(row.get("crop_uuid_id", "").strip()) == phone),
                "irrigation_tasks": count_if(active_irrigation_task_rows, lambda row, phone=phone: cropseason_uuid_to_phone.get(row.get("crop_uuid_id", "").strip()) == phone),
                "disease_reports": count_if(active_disease_report_rows, lambda row, phone=phone: row.get("user_id_id", "").strip() == phone),
                "image_recognition_records": count_if(active_vit_rows, lambda row, phone=phone: row.get("user_id_id", "").strip() == phone),
                "messages": count_if(active_message_rows, lambda row, phone=phone: row.get("user_id_id", "").strip() == phone),
            }
        )

    coverage_rows = [
        {
            "workflow_domain": "Account and field setup",
            "backend_object": "Retained operational accounts",
            "source_tables": "public_user_customuser, public_field_field, public_crop_cropseason",
            "records": len(active_user_ids),
            "linked_units": "accounts with >=1 field and >=1 crop season",
            "role_in_workflow": "Defines the cleaned account set used for operational coverage statistics.",
        },
        {
            "workflow_domain": "Account and field setup",
            "backend_object": "Vineyard fields",
            "source_tables": "public_field_field",
            "records": len(active_field_rows),
            "linked_units": f"{len(active_phones)} retained accounts",
            "role_in_workflow": "Stores field geometry, centroid, area, region, sharing, and field-level access.",
        },
        {
            "workflow_domain": "Account and field setup",
            "backend_object": "Crop seasons",
            "source_tables": "public_crop_cropseason",
            "records": len(active_cropseason_rows),
            "linked_units": f"{len(active_field_uuids)} retained fields",
            "role_in_workflow": "Links field, cultivar, cultivation method, vine age, coordinates, and season-level records.",
        },
        {
            "workflow_domain": "Environmental and analytical state",
            "backend_object": "Weather payloads",
            "source_tables": "public_weatherdata_cropweather",
            "records": len(active_weather_rows),
            "linked_units": f"{len(unique_nonempty(active_weather_rows, 'cropseason_uuid_id'))} crop seasons",
            "role_in_workflow": "Stores hourly and daily weather JSON payloads used by phenology, risk, and operation-suitability views.",
        },
        {
            "workflow_domain": "Environmental and analytical state",
            "backend_object": "Phenology payloads",
            "source_tables": "public_phendata_phendata",
            "records": len(active_phenology_rows),
            "linked_units": f"{len(unique_nonempty(active_phenology_rows, 'crop_uuid_id'))} crop seasons",
            "role_in_workflow": "Stores model-derived growth-stage trajectories attached to crop seasons.",
        },
        {
            "workflow_domain": "Environmental and analytical state",
            "backend_object": "Disease-risk outputs",
            "source_tables": "public_diseasedata_diseasedata, public_diseasedata_rb",
            "records": len(active_disease_rows) + len(active_disease_rb_rows),
            "linked_units": f"{len(unique_nonempty(active_disease_rows, 'crop_uuid_id'))} crop seasons",
            "role_in_workflow": "Stores disease-risk states and model request or response bodies for later display and replay.",
        },
        {
            "workflow_domain": "Risk delivery and field operations",
            "backend_object": "Notifications",
            "source_tables": "public_notice_notification",
            "records": len(active_notification_rows),
            "linked_units": f"{len(unique_nonempty(active_notification_rows, 'crop_uuid_id'))} crop seasons",
            "role_in_workflow": "Delivers risk, phenology, sharing, and management events to users.",
        },
        {
            "workflow_domain": "Risk delivery and field operations",
            "backend_object": "Plant-protection and irrigation tasks",
            "source_tables": "public_task_cropprotection, public_task_irrigation",
            "records": total_task_records,
            "linked_units": f"{len(unique_nonempty(active_crop_task_rows + active_irrigation_task_rows, 'crop_uuid_id'))} crop seasons",
            "role_in_workflow": "Stores pending, completed, and overdue field operations generated or managed within the crop-season workflow.",
        },
        {
            "workflow_domain": "Risk delivery and field operations",
            "backend_object": "Fungicide and pesticide records",
            "source_tables": "public_task_fungicides, public_task_pesticides",
            "records": len(active_fungicide_rows) + len(active_pesticide_rows),
            "linked_units": f"{len(active_crop_task_uuids)} plant-protection tasks",
            "role_in_workflow": "Stores product, dose, unit, and task-linked application information used as protection feedback.",
        },
        {
            "workflow_domain": "Field evidence and consultation",
            "backend_object": "Field notes and disease reports",
            "source_tables": "public_note_recode, public_note_growthstagenote, public_note_incidencenote, public_warn_discoveringdiseases",
            "records": total_notes + len(active_disease_report_rows),
            "linked_units": "crop seasons, fields, or retained accounts",
            "role_in_workflow": "Stores field observations, growth-stage notes, incidence notes, and reported disease events.",
        },
        {
            "workflow_domain": "Field evidence and consultation",
            "backend_object": "Image-analysis records",
            "source_tables": "public_vitgpt_vit, public_seg_imageupload, public_yolo_yolo_m",
            "records": total_image_records,
            "linked_units": "retained accounts or uploaded images",
            "role_in_workflow": "Stores image-recognition, segmentation, and object-detection records used as symptom-level evidence.",
        },
        {
            "workflow_domain": "Field evidence and consultation",
            "backend_object": "Advisory and message records",
            "source_tables": "public_jiaojia_jiaojia, public_message_message, public_message_jiaojiamessage, public_suggestions_suggestion",
            "records": total_advisory_records,
            "linked_units": f"{len(unique_nonempty(active_message_rows + active_advisory_message_rows + active_advisory_session_rows, 'user_id_id'))} retained accounts",
            "role_in_workflow": "Stores consultation sessions, image-associated messages, advisory messages, and suggestion records.",
        },
        {
            "workflow_domain": "Community communication",
            "backend_object": "Forum records",
            "source_tables": "public_forum_forumpost, public_forum_comment, public_forum_reply",
            "records": len(active_forum_rows),
            "linked_units": f"{len(unique_nonempty(active_forum_rows, 'user_id_id'))} retained accounts",
            "role_in_workflow": "Stores grower communication records outside the core risk-task loop.",
        },
    ]

    summary = {
        "raw_deduplicated_accounts": len(raw_user_ids),
        "retained_operational_accounts": len(active_user_ids),
        "excluded_accounts": len(raw_user_ids) - len(active_user_ids),
        "screening_rule": "Retain accounts with at least one field and at least one crop season; summarize downstream records linked to retained accounts, retained fields, retained crop seasons, or retained tasks.",
        "retained_fields": len(active_field_rows),
        "retained_crop_seasons": len(active_cropseason_rows),
        "date_ranges": {
            "fields": date_range(active_field_rows, ("created_datetime", "updated_datetime")),
            "crop_seasons": date_range(active_cropseason_rows, ("created_datetime", "updated_datetime")),
            "notifications": date_range(active_notification_rows, ("created_datetime", "updated_datetime")),
            "disease_reports": date_range(active_disease_report_rows, ("time",)),
            "image_records": date_range(active_vit_rows + segmentation_uploads + yolo_records, ("created_datetime", "updated_datetime")),
            "messages": date_range(active_message_rows + active_advisory_message_rows + active_advisory_session_rows, ("created_datetime", "updated_datetime")),
        },
    }

    write_csv(
        OUT_DIR / "backend_operational_coverage.csv",
        coverage_rows,
        ["workflow_domain", "backend_object", "source_tables", "records", "linked_units", "role_in_workflow"],
    )
    write_csv(
        OUT_DIR / "retained_operational_accounts.csv",
        retained_account_rows,
        [
            "user_id",
            "account",
            "fields",
            "crop_seasons",
            "notifications",
            "crop_protection_tasks",
            "irrigation_tasks",
            "disease_reports",
            "image_recognition_records",
            "messages",
        ],
    )

    with (OUT_DIR / "backend_operational_coverage_summary.json").open("w", encoding="utf-8") as handle:
        json.dump({"summary": summary, "coverage": coverage_rows}, handle, ensure_ascii=False, indent=2)

    md_lines = [
        "# GrapeMaster Backend Operational Coverage",
        "",
        f"- Raw deduplicated accounts: {summary['raw_deduplicated_accounts']}",
        f"- Retained operational accounts: {summary['retained_operational_accounts']}",
        f"- Excluded accounts: {summary['excluded_accounts']}",
        f"- Screening rule: {summary['screening_rule']}",
        "",
        "| Workflow domain | Backend object | Records | Linked units |",
        "| --- | --- | ---: | --- |",
    ]
    for row in coverage_rows:
        md_lines.append(
            f"| {row['workflow_domain']} | {row['backend_object']} | {row['records']} | {row['linked_units']} |"
        )
    (OUT_DIR / "backend_operational_coverage.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    latex_lines = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\small",
        "\\caption{Operational backend record coverage after account-level screening.}",
        "\\label{tab:backend_operational_coverage}",
        "\\begin{tabular}{p{0.25\\linewidth} p{0.27\\linewidth} r p{0.28\\linewidth}}",
        "\\toprule",
        "Workflow domain & Backend object & Records & Linked units \\\\",
        "\\midrule",
    ]
    for row in coverage_rows:
        latex_lines.append(
            f"{row['workflow_domain']} & {row['backend_object']} & {row['records']} & {row['linked_units']} \\\\"
        )
    latex_lines.extend(
        [
            "\\bottomrule",
            "\\end{tabular}",
            "\\end{table}",
        ]
    )
    (OUT_DIR / "backend_operational_coverage_table.tex").write_text("\n".join(latex_lines) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
