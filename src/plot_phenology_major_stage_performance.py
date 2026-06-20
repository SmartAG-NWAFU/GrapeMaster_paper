#!/usr/bin/env python3
"""Plot deployable major-stage phenology validation results."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pandas as pd

_MPL_CACHE = Path(tempfile.gettempdir()) / "grapemaster_matplotlib"
_MPL_CACHE.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_CACHE))
os.environ.setdefault("XDG_CACHE_HOME", str(_MPL_CACHE))

import matplotlib.pyplot as plt
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = ROOT / "results" / "phenology_deployable_major_stage"
FIG_DIR = ROOT / "fig"
OUT_FIG = FIG_DIR / "phenology_major_stage_validation.png"

TEXT_COLOR = "#111827"
GRID_COLOR = "#E5E7EB"
SPINE_COLOR = "#334155"

COLORS = {
    "exact": "#0F766E",
    "transition": "#8DD3C7",
    "adjacent": "#F2C94C",
    "severe": "#C2410C",
}

STAGE_LABELS = {
    "00": "BD",
    "10": "LD",
    "50": "IE",
    "60": "FL",
    "70": "FD",
    "80": "RM",
}


def load_selected_predictions() -> pd.DataFrame:
    summary = pd.read_csv(RESULT_DIR / "major_stage_candidate_summary.csv")
    selected = summary[summary["evaluation"].eq("3fold")].iloc[0]
    predictions = pd.read_csv(RESULT_DIR / "major_stage_validation_predictions.csv")
    data = predictions[
        predictions["evaluation"].eq("3fold")
        & predictions["model"].eq(selected["model"])
        & predictions["biofix_rule"].eq(selected["biofix_rule"])
        & predictions["observed_major_stage"].astype(str).ne("90")
    ].copy()
    data["observed_major_stage"] = data["observed_major_stage"].astype(str).str.zfill(2)
    data["stage_distance_abs"] = data["abs_stage_distance"].astype(float)
    return data


def outcome_summary(data: pd.DataFrame, group_col: str) -> pd.DataFrame:
    rows = []
    for name, group in data.groupby(group_col, sort=False):
        n = len(group)
        exact = group["exact_major_stage_match"].astype(bool)
        display = group["display_major_stage_match"].astype(bool)
        adjacent = group["adjacent_major_stage_match"].astype(bool)
        severe = group["severe_misclassification"].astype(bool)
        rows.append(
            {
                group_col: str(name),
                "Exact": exact.mean(),
                "Transition covered": (display & ~exact).mean(),
                "Adjacent only": (adjacent & ~display).mean(),
                "Severe mismatch": severe.mean(),
                "n": n,
            }
        )
    return pd.DataFrame(rows)


def draw_stacked(ax, table: pd.DataFrame, label_col: str, labels: list[str], panel_label: str) -> None:
    y = range(len(table))
    left = [0.0] * len(table)
    segments = ["Exact", "Transition covered", "Adjacent only", "Severe mismatch"]
    color_keys = ["exact", "transition", "adjacent", "severe"]
    for segment, color_key in zip(segments, color_keys):
        values = table[segment].to_numpy()
        ax.barh(y, values, left=left, height=0.58, color=COLORS[color_key], edgecolor="white", linewidth=0.8)
        left = [a + b for a, b in zip(left, values)]

    ax.set_yticks(list(y))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("Proportion of observations")
    ax.set_title(panel_label, loc="left", fontweight="bold", pad=1)
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.65)
    ax.tick_params(axis="both", direction="out", length=3)


def draw_distance_panel(ax, data: pd.DataFrame) -> None:
    plot_data = data.copy()
    plot_data["stage_label"] = plot_data["observed_major_stage"].map(STAGE_LABELS)
    labels = [STAGE_LABELS[s] for s in STAGE_LABELS if s in set(plot_data["observed_major_stage"])]
    values = [
        plot_data.loc[plot_data["stage_label"].eq(label), "stage_distance_abs"].mean()
        for label in labels
    ]
    y = range(len(labels))
    ax.barh(y, values, color="#BFE5DF", edgecolor="#0F766E", linewidth=0.8, height=0.58)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel("Mean absolute stage distance")
    ax.set_title("(c)", loc="left", fontweight="bold", pad=1)
    ax.set_xlim(0, max(values) * 1.18 if values else 1)
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.65)
    ax.tick_params(axis="both", direction="out", length=3)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    data = load_selected_predictions()

    plt.rcParams.update(
        {
            "font.family": "Times New Roman",
            "font.size": 7.8,
            "axes.edgecolor": SPINE_COLOR,
            "axes.labelcolor": TEXT_COLOR,
            "xtick.color": TEXT_COLOR,
            "ytick.color": TEXT_COLOR,
            "text.color": TEXT_COLOR,
            "figure.dpi": 160,
        }
    )

    fig = plt.figure(figsize=(7.08, 4.05))
    grid = fig.add_gridspec(
        2,
        2,
        height_ratios=[1.0, 1.05],
        width_ratios=[0.9, 1.3],
        hspace=0.52,
        wspace=0.36,
    )
    axes = [
        fig.add_subplot(grid[0, 0]),
        fig.add_subplot(grid[0, 1]),
        fig.add_subplot(grid[1, :]),
    ]

    cultivar = outcome_summary(data, "source_variety_code")
    cultivar = cultivar.set_index("source_variety_code").loc[["JF", "MPT", "wk"]].reset_index()
    draw_stacked(axes[0], cultivar, "source_variety_code", cultivar["source_variety_code"].tolist(), "(a)")

    stage = outcome_summary(data, "observed_major_stage")
    stage_order = [s for s in STAGE_LABELS if s in set(stage["observed_major_stage"])]
    stage = stage.set_index("observed_major_stage").loc[stage_order].reset_index()
    draw_stacked(axes[1], stage, "observed_major_stage", [STAGE_LABELS[s] for s in stage_order], "(b)")

    draw_distance_panel(axes[2], data)

    legend_items = [
        Patch(facecolor=COLORS["exact"], edgecolor="white", label="Exact"),
        Patch(facecolor=COLORS["transition"], edgecolor="white", label="Transition covered"),
        Patch(facecolor=COLORS["adjacent"], edgecolor="white", label="Adjacent only"),
        Patch(facecolor=COLORS["severe"], edgecolor="white", label="Severe mismatch"),
    ]
    fig.legend(
        handles=legend_items,
        loc="lower center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, 0.0),
        fontsize=7.8,
        handlelength=1.2,
        columnspacing=1.0,
    )

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.subplots_adjust(left=0.08, right=0.985, top=0.96, bottom=0.16)
    fig.savefig(OUT_FIG, dpi=600)
    print(f"Wrote {OUT_FIG}")


if __name__ == "__main__":
    main()
