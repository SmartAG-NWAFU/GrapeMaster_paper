#!/usr/bin/env python3
"""Plot core analytical support results for the GrapeMaster paper.

The figure combines two deployed analytical supports used by GrapeMaster:
FSIM-S for downy-mildew infection-risk prediction and the grape disease
image-recognition model. The output keeps a double-column journal width.
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path

_MPL_CACHE = Path(tempfile.gettempdir()) / "grapemaster_matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))
os.environ.setdefault("XDG_CACHE_HOME", str(_MPL_CACHE))

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
FSIMS_DIR = ROOT / "data" / "fsims"
DETECTION_DIR = ROOT / "data" / "disease_detection_fig_data"
FIG_DIR = ROOT / "fig"
RESULT_DIR = ROOT / "results"

OUT_FIG = FIG_DIR / "fsims_supporting_performance.png"
OUT_SUMMARY = RESULT_DIR / "core_analytical_support_summary.csv"

FSIMS_COLOR = "#0F766E"
DETECTION_COLOR = "#7C3AED"
ACCENT_COLOR = "#9F1239"
GRID_COLOR = "#E5E7EB"
TEXT_COLOR = "#111827"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_fsims_validation_metrics() -> list[dict[str, float | str]]:
    fsims = read_json(FSIMS_DIR / "final_spore_params.json")["metrics_seed_summary"]
    return [
        {
            "metric": "Validation MAE",
            "unit": "days",
            "value": float(fsims["val_mae_mean"]),
            "detail": f"{int(float(fsims['n_folds']))}-fold mean +/- SD",
        },
        {
            "metric": "Validation RMSE",
            "unit": "days",
            "value": float(fsims["val_rmse"]),
            "detail": "overall validation RMSE",
        },
    ]


def load_detection_metrics() -> tuple[dict[str, str], list[dict[str, str]]]:
    overall_rows = read_csv(DETECTION_DIR / "train_val_test_overall.csv")
    test_overall = next(row for row in overall_rows if row["Split"].lower() == "test")
    class_rows = read_csv(DETECTION_DIR / "disease_metrics_test.csv")
    return test_overall, class_rows


def draw_fsims_panel(ax, fsims_metrics: list[dict[str, float | str]]) -> None:
    y_positions = [0.0, 0.62]
    for y, row in zip(y_positions, fsims_metrics):
        value = float(row["value"])
        ax.barh(y, value, height=0.34, color="#BFE5DF", edgecolor=FSIMS_COLOR, linewidth=0.9, zorder=2)
        ax.scatter(value, y, s=108, color=FSIMS_COLOR, edgecolor="white", linewidth=0.9, zorder=4)

    ax.set_yticks(y_positions)
    ax.set_yticklabels([str(row["metric"]) for row in fsims_metrics])
    ax.invert_yaxis()
    ax.set_ylim(0.86, -0.24)
    ax.set_xlim(0, 8.4)
    ax.set_xlabel("Prediction error (days)")
    ax.set_title("(a)", loc="left", fontweight="bold")
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.7)
    ax.tick_params(axis="both", direction="out", length=3)


def draw_detection_panel(ax, test_overall: dict[str, str], class_rows: list[dict[str, str]]) -> None:
    rows = sorted(class_rows, key=lambda row: float(row["F1-Score"]))
    labels = [row["Disease"] for row in rows]
    values = [float(row["F1-Score"]) for row in rows]
    y_positions = list(range(len(rows)))

    for y, row, value in zip(y_positions, rows, values):
        is_downy = row["Disease"] == "Downy Mildew"
        ax.barh(
            y,
            value,
            height=0.52,
            color="#E5D8FF",
            edgecolor="#BFA7FF",
            linewidth=1.7 if is_downy else 0.6,
            zorder=2,
        )
    ax.scatter(values, y_positions, s=126, color=DETECTION_COLOR, edgecolor="white", linewidth=1.0, zorder=3)
    for y, value in zip(y_positions, values):
        ax.text(value + 0.004, y, f"{value:.3f}", ha="left", va="center", fontsize=9.5, color=DETECTION_COLOR)

    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels)
    for tick, label in zip(ax.get_yticklabels(), labels):
        if label == "Downy Mildew":
            tick.set_fontweight("bold")
    ax.set_xlim(0.90, 1.005)
    ax.set_xlabel("Class-wise F1-score")
    ax.set_title("(b)", loc="left", fontweight="bold")
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.7)
    ax.tick_params(axis="both", direction="out", length=3)


def write_summary(
    fsims_metrics: list[dict[str, float | str]], test_overall: dict[str, str], class_rows: list[dict[str, str]]
) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for row in fsims_metrics:
        value = float(row["value"])
        rows.append(
            {
                "module": "FSIM-S",
                "metric": str(row["metric"]),
                "value": f"{value:.3f}",
                "reference_value": "",
                "note": str(row["detail"]),
            }
        )
    for key in ["Accuracy", "Precision", "Recall", "F1-Score"]:
        rows.append(
            {
                "module": "Disease recognition",
                "metric": f"Test {key}",
                "value": f"{float(test_overall[key]):.3f}",
                "reference_value": "",
                "note": f"n={int(float(test_overall['Samples']))}",
            }
        )
    for row in class_rows:
        rows.append(
            {
                "module": "Disease recognition",
                "metric": f"{row['Disease']} F1-score",
                "value": f"{float(row['F1-Score']):.3f}",
                "reference_value": "",
                "note": "test class",
            }
        )

    with OUT_SUMMARY.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["module", "metric", "value", "reference_value", "note"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fsims_metrics = load_fsims_validation_metrics()
    test_overall, class_rows = load_detection_metrics()

    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.size": 10,
            "axes.edgecolor": "#334155",
            "axes.labelcolor": TEXT_COLOR,
            "xtick.color": TEXT_COLOR,
            "ytick.color": TEXT_COLOR,
            "text.color": TEXT_COLOR,
            "figure.dpi": 160,
        }
    )

    fig, axes = plt.subplots(
        2,
        1,
        figsize=(7.08, 4.65),
        gridspec_kw={"height_ratios": [0.88, 1.58], "hspace": 0.42},
    )
    draw_fsims_panel(axes[0], fsims_metrics)
    draw_detection_panel(axes[1], test_overall, class_rows)

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.savefig(OUT_FIG, dpi=600, bbox_inches="tight")
    write_summary(fsims_metrics, test_overall, class_rows)
    print(f"Wrote {OUT_FIG}")
    print(f"Wrote {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
