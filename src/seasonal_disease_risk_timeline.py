from __future__ import annotations

import argparse
import csv
import json
from datetime import timedelta
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESPONSE_JSON = ROOT / "diseasemodel" / "test" / "mingyang" / "data" / "2024_grape_response.json"
DEFAULT_REQUEST_JSON = ROOT / "diseasemodel" / "test" / "mingyang" / "data" / "2024_grape_rb.json"
DEFAULT_TIMELINE_CSV = ROOT / "data" / "seasonal_disease_risk_timeline.csv"
DEFAULT_OUTPUT_FIG = ROOT / "fig" / "seasonal_disease_risk_timeline.png"
DEFAULT_SITE_LABEL = "Mingyang, Guangxi"
DEFAULT_DATASETS = [
    {
        "name": "Mingyang 2024",
        "site": "Mingyang, Guangxi",
        "response": DEFAULT_RESPONSE_JSON,
        "request": DEFAULT_REQUEST_JSON,
    },
    {
        "name": "GXG-233 without fungicide",
        "site": "GXG-233, Guangxi",
        "response": ROOT / "diseasemodel" / "test" / "GXG-233" / "data" / "rsb_without_fun.json",
        "request": ROOT / "diseasemodel" / "test" / "GXG-233" / "data" / "rb_without_fun.json",
    },
    {
        "name": "GXG-233 with fungicide",
        "site": "GXG-233, Guangxi",
        "response": ROOT / "diseasemodel" / "test" / "GXG-233" / "data" / "rsb_with_fun.json",
        "request": ROOT / "diseasemodel" / "test" / "GXG-233" / "data" / "rb_with_fun.json",
    },
]

TRACKS = [
    ("PLASVI", "Downy mildew", 2),
    ("UNCINE", "Powdery mildew", 1),
    ("FIELD", "Field risk", 0),
]

RISK_COLOR_MAP = {
    "NOT_SEASONAL": "#d4d7dc",
    "UNFAVORABLE": "#2b8c7f",
    "FAVORABLE": "#e4b43f",
    "OPTIMAL": "#c9473a",
    "PROTECTED": "#3b78b8",
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_timeline_rows(response: dict, dataset_name: str = "", site_note: str = "") -> list[dict[str, str]]:
    rows = []

    stress_risks = pd.DataFrame(response["stressRisks"])
    field_risks = pd.DataFrame(response["fieldRisks"])

    for stress_id, track, _ in TRACKS:
        if stress_id == "FIELD":
            for record in field_risks.sort_values("referenceDate").to_dict("records"):
                rows.append(
                    {
                        "date": record["referenceDate"],
                        "dataset": dataset_name,
                        "site": site_note,
                        "track": track,
                        "stress_id": "",
                        "risk_code": record["riskCode"],
                    }
                )
            continue

        stress_records = stress_risks.loc[stress_risks["stressId"] == stress_id].sort_values("referenceDate")
        for record in stress_records.to_dict("records"):
            rows.append(
                {
                    "date": record["referenceDate"],
                    "dataset": dataset_name,
                    "site": site_note,
                    "track": track,
                    "stress_id": stress_id,
                    "risk_code": record["riskCode"],
                }
            )

    return rows


def write_timeline_csv(rows: list[dict[str, str]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "dataset", "site", "track", "stress_id", "risk_code"])
        writer.writeheader()
        writer.writerows(rows)


def load_spray_dates(request_json: Path | None) -> list[pd.Timestamp]:
    if request_json is None or not request_json.exists():
        return []

    request = load_json(request_json)
    spray_dates = []
    for fungicide in request.get("applied_fungicides", []):
        applied_date = fungicide.get("applied_date")
        if applied_date:
            spray_dates.append(pd.to_datetime(applied_date))
    return sorted(set(spray_dates))


def load_site_note(request_json: Path | None, site_label: str) -> str:
    if request_json is None or not request_json.exists():
        return site_label

    request = load_json(request_json)
    latitude = request.get("latitude")
    longitude = request.get("longitude")
    if latitude is None or longitude is None:
        return site_label
    return f"{site_label} ({latitude:.2f} N, {longitude:.2f} E)"


def build_default_rows_and_sprays() -> tuple[list[dict[str, str]], dict[str, list[pd.Timestamp]]]:
    rows = []
    spray_dates_by_dataset = {}
    for dataset in DEFAULT_DATASETS:
        response = load_json(dataset["response"])
        site_note = load_site_note(dataset["request"], dataset["site"])
        rows.extend(build_timeline_rows(response, dataset["name"], site_note))
        spray_dates_by_dataset[dataset["name"]] = load_spray_dates(dataset["request"])
    return rows, spray_dates_by_dataset


def iter_risk_segments(group: pd.DataFrame) -> list[tuple[pd.Timestamp, pd.Timestamp, str]]:
    group = group.sort_values("date").reset_index(drop=True)
    if group.empty:
        return []

    segments = []
    start_date = group.loc[0, "date"]
    previous_date = start_date
    previous_risk = group.loc[0, "risk_code"]

    for record in group.iloc[1:].itertuples(index=False):
        current_date = record.date
        current_risk = record.risk_code
        if current_risk != previous_risk:
            segments.append((start_date, previous_date + timedelta(days=1), previous_risk))
            start_date = current_date
            previous_risk = current_risk
        previous_date = current_date

    segments.append((start_date, previous_date + timedelta(days=1), previous_risk))
    return segments


def add_inside_legend(ax: plt.Axes) -> None:
    legend_items = list(RISK_COLOR_MAP.items())
    x0 = 0.07
    y0 = 0.935
    item_width = 0.19
    swatch_width = 0.024
    swatch_height = 0.036

    for index, (label, color) in enumerate(legend_items):
        x = x0 + index * item_width
        ax.add_patch(
            Rectangle(
                (x, y0),
                swatch_width,
                swatch_height,
                transform=ax.transAxes,
                facecolor=color,
                edgecolor="#333333",
                linewidth=0.25,
                clip_on=False,
            )
        )
        ax.text(
            x + swatch_width + 0.008,
            y0 + swatch_height / 2,
            label.replace("_", " "),
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=10,
            color="#202020",
        )


def plot_timeline(
    rows: list[dict[str, str]],
    spray_dates_by_dataset: dict[str, list[pd.Timestamp]],
    output_fig: Path,
) -> None:
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "axes.titlesize": 14,
            "axes.labelsize": 13,
            "xtick.labelsize": 11,
            "ytick.labelsize": 13,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    dataset_names = list(dict.fromkeys(df["dataset"].tolist()))

    fig_height = 0.95 + len(dataset_names) * 1.95
    fig, axes = plt.subplots(len(dataset_names), 1, figsize=(9.2, fig_height), sharex=False)
    if len(dataset_names) == 1:
        axes = [axes]
    fig.patch.set_facecolor("white")
    track_height = 0.56

    panel_labels = ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)"]

    for axis_index, (ax, dataset_name) in enumerate(zip(axes, dataset_names)):
        ax.set_facecolor("white")
        group_df = df.loc[df["dataset"] == dataset_name].copy()
        site_note = group_df["site"].iloc[0]

        for _, track, y in TRACKS:
            track_group = group_df.loc[group_df["track"] == track].sort_values("date")
            for start_date, end_date, risk_code in iter_risk_segments(track_group):
                ax.broken_barh(
                    [(mdates.date2num(start_date), mdates.date2num(end_date) - mdates.date2num(start_date))],
                    (y - track_height / 2, track_height),
                    facecolors=RISK_COLOR_MAP[risk_code],
                    edgecolors="white",
                    linewidth=0.7,
                )

        spray_dates = spray_dates_by_dataset.get(dataset_name, [])
        for spray_date in spray_dates:
            ax.vlines(
                spray_date,
                -track_height / 2,
                2 + track_height / 2,
                color="#202020",
                linewidth=0.8,
                linestyle=(0, (3, 2)),
                alpha=0.75,
            )
        if spray_dates:
            ax.text(spray_dates[0], 2.38, "Fungicide", fontsize=12, ha="left", va="bottom", color="#202020")

        min_date = group_df["date"].min()
        max_date = group_df["date"].max() + timedelta(days=1)
        ax.set_xlim(min_date, max_date)
        ax.set_ylim(-0.55, 3.15)
        ax.set_yticks([0, 1, 2])
        ax.set_yticklabels(["Field risk", "Powdery mildew", "Downy mildew"])
        ax.grid(axis="x", color="#e7e8eb", linewidth=0.65)
        ax.grid(axis="y", visible=False)
        major_interval = 15 if axis_index == 0 else 30
        minor_interval = 5 if axis_index == 0 else 10
        ax.xaxis.set_major_locator(mdates.DayLocator(interval=major_interval))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.xaxis.set_minor_locator(mdates.DayLocator(interval=minor_interval))

        ax.text(
            0.01,
            0.98,
            panel_labels[axis_index],
            transform=ax.transAxes,
            ha="left",
            va="top",
            fontsize=14,
            fontweight="bold",
            color="#202020",
        )
        if axis_index == 0:
            add_inside_legend(ax)

        for spine in ["top", "right"]:
            ax.spines[spine].set_visible(False)
        ax.spines["left"].set_visible(True)
        ax.spines["left"].set_color("#333333")
        ax.spines["left"].set_linewidth(0.8)
        ax.spines["bottom"].set_color("#333333")
        ax.spines["bottom"].set_linewidth(0.8)
        ax.tick_params(axis="y", length=3.0, width=0.7, color="#333333", pad=8)
        ax.tick_params(axis="x", which="major", length=3.5, width=0.7, color="#333333")
        ax.tick_params(axis="x", which="minor", length=2.0, width=0.5, color="#777777")

    axes[-1].set_xlabel("Date")

    output_fig.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(h_pad=1.0)
    fig.savefig(output_fig, dpi=300, bbox_inches="tight")
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot grape disease-risk timeline from diseasemodel output.")
    parser.add_argument("--response-json", type=Path, default=DEFAULT_RESPONSE_JSON)
    parser.add_argument("--request-json", type=Path, default=DEFAULT_REQUEST_JSON)
    parser.add_argument("--timeline-csv", type=Path, default=DEFAULT_TIMELINE_CSV)
    parser.add_argument("--output-fig", type=Path, default=DEFAULT_OUTPUT_FIG)
    parser.add_argument("--site-label", default=DEFAULT_SITE_LABEL)
    parser.add_argument("--single", action="store_true", help="Plot only --response-json and --request-json.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.single:
        site_note = load_site_note(args.request_json, args.site_label)
        response = load_json(args.response_json)
        rows = build_timeline_rows(response, args.site_label, site_note)
        spray_dates_by_dataset = {args.site_label: load_spray_dates(args.request_json)}
    else:
        rows, spray_dates_by_dataset = build_default_rows_and_sprays()
    write_timeline_csv(rows, args.timeline_csv)
    plot_timeline(rows, spray_dates_by_dataset, args.output_fig)
    print(f"Wrote timeline data: {args.timeline_csv}")
    print(f"Wrote figure: {args.output_fig}")


if __name__ == "__main__":
    main()
