from __future__ import annotations

import argparse
import csv
import json
from datetime import timedelta
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from matplotlib.patches import Rectangle
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESPONSE_JSON = ROOT / "diseasemodel" / "test" / "mingyang" / "data" / "2024_grape_response.json"
DEFAULT_REQUEST_JSON = ROOT / "diseasemodel" / "test" / "mingyang" / "data" / "2024_grape_rb.json"
DEFAULT_TIMELINE_CSV = ROOT / "data" / "seasonal_disease_risk_timeline.csv"
DEFAULT_OUTPUT_FIG = ROOT / "fig" / "disease_risk_timeline_downy_field.png"
DEFAULT_NOTIFICATION_FIG = ROOT / "fig" / "alert_notification_interfaces.png"
DEFAULT_SITE_LABEL = "Mingyang, Guangxi"
DOUBLE_COLUMN_WIDTH_IN = 7.1
FIGURE_DPI = 300
DEFAULT_DATASETS = [
    {
        "name": "Mingyang 2024",
        "site": "Mingyang, Guangxi",
        "response": DEFAULT_RESPONSE_JSON,
        "request": DEFAULT_REQUEST_JSON,
    },
    {
        "name": "Guangxi case without fungicide feedback",
        "site": "Guangxi crop-season case",
        "response": ROOT / "diseasemodel" / "test" / "GXG-233" / "data" / "rsb_without_fun.json",
        "request": ROOT / "diseasemodel" / "test" / "GXG-233" / "data" / "rb_without_fun.json",
    },
    {
        "name": "Guangxi case with fungicide feedback",
        "site": "Guangxi crop-season case",
        "response": ROOT / "diseasemodel" / "test" / "GXG-233" / "data" / "rsb_with_fun.json",
        "request": ROOT / "diseasemodel" / "test" / "GXG-233" / "data" / "rb_with_fun.json",
    },
]

TRACKS = [
    ("PLASVI", "Downy mildew", 1),
    ("FIELD", "Field risk", 0),
]

RISK_COLOR_MAP = {
    "NOT_SEASONAL": "#d4d7dc",
    "UNFAVORABLE": "#2b8c7f",
    "FAVORABLE": "#e4b43f",
    "OPTIMAL": "#c9473a",
    "PROTECTED": "#3b78b8",
}

RISK_LABEL_MAP = {
    "NOT_SEASONAL": "Not seasonal",
    "UNFAVORABLE": "Unfavorable",
    "FAVORABLE": "Favorable",
    "OPTIMAL": "Optimal",
    "PROTECTED": "Protected",
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


def read_timeline_csv(input_csv: Path) -> list[dict[str, str]]:
    allowed_tracks = {track for _, track, _ in TRACKS}
    with input_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return [row for row in reader if row.get("track") in allowed_tracks]


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
    positions = [
        (0.13, 0.970),
        (0.40, 0.970),
        (0.67, 0.970),
        (0.13, 0.842),
        (0.40, 0.842),
    ]
    swatch_width = 0.020
    swatch_height = 0.028

    for (label, color), (x, y) in zip(legend_items, positions):
        ax.add_patch(
            Rectangle(
                (x, y),
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
            y + swatch_height / 2,
            RISK_LABEL_MAP.get(label, label.replace("_", " ").title()),
            transform=ax.transAxes,
            ha="left",
            va="center",
            fontsize=8.2,
            color="#202020",
        )


def add_fungicide_icon(
    ax: plt.Axes,
    track_group: pd.DataFrame,
    icon_path: Path,
    zoom: float = 0.16,
) -> None:
    protected_segments = [
        (start_date, end_date)
        for start_date, end_date, risk_code in iter_risk_segments(track_group)
        if risk_code == "PROTECTED"
    ]
    if not protected_segments or not icon_path.exists():
        return

    start_date, end_date = protected_segments[0]
    midpoint = start_date + (end_date - start_date) / 2
    icon = Image.open(icon_path).convert("RGBA")
    image_box = OffsetImage(icon, zoom=zoom, interpolation="lanczos")
    annotation = AnnotationBbox(
        image_box,
        (mdates.date2num(midpoint), 2.02),
        xycoords="data",
        frameon=False,
        box_alignment=(0.5, 0.5),
        pad=0,
        zorder=20,
    )
    ax.add_artist(annotation)
    ax.annotate(
        "",
        xy=(mdates.date2num(midpoint), 1.34),
        xytext=(mdates.date2num(midpoint), 1.70),
        xycoords="data",
        textcoords="data",
        arrowprops={
            "arrowstyle": "-|>",
            "color": "#202020",
            "linewidth": 0.8,
            "mutation_scale": 8,
            "shrinkA": 0,
            "shrinkB": 0,
        },
        zorder=19,
    )


def plot_timeline(
    rows: list[dict[str, str]],
    spray_dates_by_dataset: dict[str, list[pd.Timestamp]],
    output_fig: Path,
    figure_width: float = DOUBLE_COLUMN_WIDTH_IN,
    fungicide_icon: Path | None = None,
) -> None:
    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "axes.titlesize": 12,
            "axes.labelsize": 12,
            "xtick.labelsize": 10,
            "ytick.labelsize": 12,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
        }
    )

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    dataset_names = list(dict.fromkeys(df["dataset"].tolist()))

    fig_height = 0.72 + len(dataset_names) * 1.26
    fig, axes = plt.subplots(len(dataset_names), 1, figsize=(figure_width, fig_height), sharex=False)
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
            if axis_index == 2 and track == "Downy mildew" and fungicide_icon is not None:
                add_fungicide_icon(ax, track_group, fungicide_icon)

        spray_dates = spray_dates_by_dataset.get(dataset_name, [])
        for spray_date in spray_dates:
            ax.vlines(
                spray_date,
                -track_height / 2,
                1 + track_height / 2,
                color="#202020",
                linewidth=0.8,
                linestyle=(0, (3, 2)),
                alpha=0.75,
            )
        if spray_dates:
            ax.text(spray_dates[0], 1.38, "Fungicide", fontsize=12, ha="left", va="bottom", color="#202020")

        min_date = group_df["date"].min()
        max_date = group_df["date"].max() + timedelta(days=1)
        ax.set_xlim(min_date, max_date)
        ax.set_ylim(-0.55, 2.15)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["Field risk", "Downy mildew"])
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
            fontsize=12,
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
    fig.tight_layout(h_pad=0.68)
    fig.savefig(output_fig, dpi=FIGURE_DPI, bbox_inches="tight")
    plt.close(fig)


def compose_timeline_notification_figure(
    timeline_fig: Path,
    notification_fig: Path,
    output_fig: Path,
    target_width: int = round(DOUBLE_COLUMN_WIDTH_IN * FIGURE_DPI),
    max_height: int = round(9.2 * FIGURE_DPI),
) -> None:
    timeline = Image.open(timeline_fig).convert("RGBA")
    notification = Image.open(notification_fig).convert("RGBA")

    def scale_to_width(image: Image.Image, width: int) -> Image.Image:
        ratio = width / image.width
        return image.resize((width, round(image.height * ratio)), Image.Resampling.LANCZOS)

    timeline = scale_to_width(timeline, target_width)

    padding = round(0.18 * FIGURE_DPI)
    available_notification_height = max_height - timeline.height - padding
    notification_by_width = scale_to_width(notification, target_width)
    if notification_by_width.height > available_notification_height:
        ratio = available_notification_height / notification.height
        notification = notification.resize(
            (round(notification.width * ratio), available_notification_height),
            Image.Resampling.LANCZOS,
        )
    else:
        notification = notification_by_width

    canvas_height = timeline.height + notification.height + padding
    canvas = Image.new("RGBA", (target_width, canvas_height), "WHITE")
    canvas.alpha_composite(timeline, (0, 0))
    notification_x = round((target_width - notification.width) / 2)
    canvas.alpha_composite(notification, (notification_x, timeline.height + padding))

    output_fig.parent.mkdir(parents=True, exist_ok=True)
    ImageOps.expand(canvas.convert("RGB"), border=0, fill="white").save(output_fig, dpi=(FIGURE_DPI, FIGURE_DPI))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plot grape disease-risk timeline from diseasemodel output.")
    parser.add_argument("--response-json", type=Path, default=DEFAULT_RESPONSE_JSON)
    parser.add_argument("--request-json", type=Path, default=DEFAULT_REQUEST_JSON)
    parser.add_argument("--timeline-csv", type=Path, default=DEFAULT_TIMELINE_CSV)
    parser.add_argument("--output-fig", type=Path, default=DEFAULT_OUTPUT_FIG)
    parser.add_argument("--notification-fig", type=Path, default=DEFAULT_NOTIFICATION_FIG)
    parser.add_argument(
        "--combined-output-fig",
        type=Path,
        default=None,
        help="Optional output path for a stacked timeline + notification composite figure.",
    )
    parser.add_argument("--site-label", default=DEFAULT_SITE_LABEL)
    parser.add_argument(
        "--fungicide-icon",
        type=Path,
        default=None,
        help="Optional icon to place above the protected downy mildew segment in panel c.",
    )
    parser.add_argument("--single", action="store_true", help="Plot only --response-json and --request-json.")
    parser.add_argument(
        "--from-csv",
        action="store_true",
        help="Read --timeline-csv directly instead of rebuilding rows from disease-model JSON files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.from_csv:
        rows = read_timeline_csv(args.timeline_csv)
        spray_dates_by_dataset = {}
    elif args.single:
        site_note = load_site_note(args.request_json, args.site_label)
        response = load_json(args.response_json)
        rows = build_timeline_rows(response, args.site_label, site_note)
        spray_dates_by_dataset = {args.site_label: load_spray_dates(args.request_json)}
    else:
        rows, spray_dates_by_dataset = build_default_rows_and_sprays()
    if not args.from_csv:
        write_timeline_csv(rows, args.timeline_csv)
    plot_timeline(rows, spray_dates_by_dataset, args.output_fig, fungicide_icon=args.fungicide_icon)
    if not args.from_csv:
        print(f"Wrote timeline data: {args.timeline_csv}")
    print(f"Wrote figure: {args.output_fig}")
    if args.combined_output_fig is not None:
        compose_timeline_notification_figure(args.output_fig, args.notification_fig, args.combined_output_fig)
        print(f"Wrote combined figure: {args.combined_output_fig}")


if __name__ == "__main__":
    main()
