#!/usr/bin/env python3
"""Plot compact FSIM-S performance evidence for the GrapeMaster paper.

This script intentionally uses a different visual form from the FSIM-S
manuscript figure in data/fsims/Figure_11.png. It summarizes the error
reduction of the spore-pressure-adjusted FSIM-S model against the baseline
FSIM across calibration seeds and highlights the selected model used as the
platform risk engine.
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
DATA_DIR = ROOT / "data" / "fsims"
FIG_DIR = ROOT / "fig"
RESULT_DIR = ROOT / "results"


BASELINE_COLOR = "#4A5568"
FSIMS_COLOR = "#0F766E"
IMPROVEMENT_COLOR = "#9F1239"
GRID_COLOR = "#E5E7EB"
TEXT_COLOR = "#111827"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def as_float(row: dict, key: str) -> float:
    return float(row[key])


def pct_reduction(baseline: float, fsims: float) -> float:
    if baseline == 0:
        return 0.0
    return (baseline - fsims) / baseline * 100.0


def write_summary(rows: list[dict[str, str]], baseline_json: dict, fsims_json: dict) -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    out = RESULT_DIR / "fsims_supporting_performance_summary.csv"
    fieldnames = [
        "seed",
        "metric",
        "baseline_error_days",
        "fsims_error_days",
        "absolute_reduction_days",
        "relative_reduction_percent",
    ]
    summary_rows: list[dict[str, object]] = []
    for row in rows:
        seed = row["seed"]
        for metric, b_key, s_key in [
            ("Validation MAE", "val_mae_mean_baseline", "val_mae_mean_spore"),
            ("Validation RMSE", "val_rmse_baseline", "val_rmse_spore"),
            ("Training MAE", "train_mae_mean_baseline", "train_mae_mean_spore"),
            ("Training RMSE", "train_rmse_baseline", "train_rmse_spore"),
        ]:
            b_val = as_float(row, b_key)
            s_val = as_float(row, s_key)
            summary_rows.append(
                {
                    "seed": seed,
                    "metric": metric,
                    "baseline_error_days": f"{b_val:.3f}",
                    "fsims_error_days": f"{s_val:.3f}",
                    "absolute_reduction_days": f"{b_val - s_val:.3f}",
                    "relative_reduction_percent": f"{pct_reduction(b_val, s_val):.2f}",
                }
            )

    selected_seed = str(int(float(fsims_json["selected_seed"])))
    b = baseline_json["metrics_seed_summary"]
    s = fsims_json["metrics_seed_summary"]
    for metric, b_key, s_key in [
        ("Selected train MAE", "train_mae_mean", "train_mae_mean"),
        ("Selected validation MAE", "val_mae_mean", "val_mae_mean"),
        ("Selected train RMSE", "train_rmse", "train_rmse"),
        ("Selected validation RMSE", "val_rmse", "val_rmse"),
    ]:
        b_val = float(b[b_key])
        s_val = float(s[s_key])
        summary_rows.append(
            {
                "seed": selected_seed,
                "metric": metric,
                "baseline_error_days": f"{b_val:.3f}",
                "fsims_error_days": f"{s_val:.3f}",
                "absolute_reduction_days": f"{b_val - s_val:.3f}",
                "relative_reduction_percent": f"{pct_reduction(b_val, s_val):.2f}",
            }
        )

    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)


def draw_panel_a(ax, rows: list[dict[str, str]]) -> None:
    metric_specs = [
        ("Validation MAE", "val_mae_mean_baseline", "val_mae_mean_spore"),
        ("Validation RMSE", "val_rmse_baseline", "val_rmse_spore"),
    ]
    y_positions: list[float] = []
    y_labels: list[str] = []
    y = 0.0
    for metric_label, b_key, s_key in metric_specs:
        for row in rows:
            seed = row["seed"]
            b_val = as_float(row, b_key)
            s_val = as_float(row, s_key)
            ax.plot([s_val, b_val], [y, y], color="#CBD5E1", lw=2.2, solid_capstyle="round", zorder=1)
            ax.scatter(b_val, y, s=58, color=BASELINE_COLOR, edgecolor="white", linewidth=0.7, zorder=3)
            ax.scatter(s_val, y, s=64, color=FSIMS_COLOR, edgecolor="white", linewidth=0.7, zorder=4)
            reduction = pct_reduction(b_val, s_val)
            ax.text(
                max(b_val, s_val) + 0.35,
                y,
                f"{reduction:.1f}%",
                va="center",
                ha="left",
                color=IMPROVEMENT_COLOR,
                fontsize=9,
            )
            y_positions.append(y)
            y_labels.append(f"{metric_label.replace('Validation ', '')}, seed {seed}")
            y += 1.0
        y += 0.55

    ax.set_yticks(y_positions)
    ax.set_yticklabels(y_labels)
    ax.invert_yaxis()
    ax.set_xlabel("Error (days)")
    ax.set_title("(a) Validation-error reduction across calibration seeds", loc="left", fontweight="bold")
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.7)
    ax.set_xlim(3.0, 12.0)
    ax.tick_params(axis="both", direction="out", length=3)

    legend_handles = [
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=BASELINE_COLOR, markersize=7, label="FSIM"),
        plt.Line2D([0], [0], marker="o", color="none", markerfacecolor=FSIMS_COLOR, markersize=7, label="FSIM-S"),
        plt.Line2D([0], [0], color=IMPROVEMENT_COLOR, lw=0, label="Label = relative reduction"),
    ]
    ax.legend(
        handles=legend_handles,
        frameon=False,
        loc="upper center",
        bbox_to_anchor=(0.50, -0.16),
        ncol=3,
        fontsize=9,
        handletextpad=0.4,
        columnspacing=1.2,
    )


def draw_panel_b(ax, baseline_json: dict, fsims_json: dict) -> None:
    b = baseline_json["metrics_seed_summary"]
    s = fsims_json["metrics_seed_summary"]
    metrics = [
        ("Train MAE", "train_mae_mean"),
        ("Validation MAE", "val_mae_mean"),
        ("Train RMSE", "train_rmse"),
        ("Validation RMSE", "val_rmse"),
    ]

    y_positions = list(range(len(metrics)))
    for y, (label, key) in zip(y_positions, metrics):
        b_val = float(b[key])
        s_val = float(s[key])
        ax.plot([s_val, b_val], [y, y], color="#CBD5E1", lw=3.0, solid_capstyle="round", zorder=1)
        ax.scatter(b_val, y, s=84, color=BASELINE_COLOR, edgecolor="white", linewidth=0.8, zorder=3)
        ax.scatter(s_val, y, s=92, color=FSIMS_COLOR, edgecolor="white", linewidth=0.8, zorder=4)
        ax.text(
            s_val - 0.28,
            y,
            f"{s_val:.1f}",
            va="center",
            ha="right",
            color=FSIMS_COLOR,
            fontsize=9,
        )
        ax.text(
            b_val + 0.28,
            y,
            f"{b_val:.1f}",
            va="center",
            ha="left",
            color=BASELINE_COLOR,
            fontsize=9,
        )

    selected_seed = int(float(fsims_json["selected_seed"]))
    val_mae_reduction = pct_reduction(float(b["val_mae_mean"]), float(s["val_mae_mean"]))
    val_rmse_reduction = pct_reduction(float(b["val_rmse"]), float(s["val_rmse"]))
    ax.text(
        0.01,
        -0.30,
        (
            f"Selected seed: {selected_seed}; "
            f"validation MAE = {float(s['val_mae_mean']):.1f} d ({val_mae_reduction:.1f}% lower); "
            f"validation RMSE = {float(s['val_rmse']):.1f} d ({val_rmse_reduction:.1f}% lower)."
        ),
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color="#475569",
    )
    ax.set_yticks(y_positions)
    ax.set_yticklabels([m[0] for m in metrics])
    ax.invert_yaxis()
    ax.set_xlabel("Error (days)")
    ax.set_title("(b) Selected FSIM-S engine summary", loc="left", fontweight="bold")
    ax.grid(axis="x", color=GRID_COLOR, linewidth=0.7)
    ax.set_xlim(3.0, 11.5)
    ax.tick_params(axis="both", direction="out", length=3)


def main() -> None:
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    rows = read_csv(DATA_DIR / "baseline_vs_spore_seed_compare.csv")
    baseline_json = read_json(DATA_DIR / "final_baseline_params.json")
    fsims_json = read_json(DATA_DIR / "final_spore_params.json")

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
        figsize=(7.08, 5.15),
        gridspec_kw={"height_ratios": [1.35, 1.0], "hspace": 0.62},
    )
    draw_panel_a(axes[0], rows)
    draw_panel_b(axes[1], baseline_json, fsims_json)

    for ax in axes:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    fig.tight_layout(rect=[0.0, 0.06, 1.0, 1.0])

    out = FIG_DIR / "fsims_supporting_performance.png"
    fig.savefig(out, dpi=600, bbox_inches="tight")
    write_summary(rows, baseline_json, fsims_json)
    print(f"Wrote {out}")
    print(f"Wrote {RESULT_DIR / 'fsims_supporting_performance_summary.csv'}")


if __name__ == "__main__":
    main()
