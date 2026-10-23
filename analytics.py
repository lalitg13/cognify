"""
analytics.py - Headless Pandas + Matplotlib Dark-Mode Telemetry Engine
Generates high-contrast, publication-grade academic telemetry graphics for Cognify.
Supports multi-panel views: 'mastery' (retention curves) and 'diagnostics' (weak-spot frequency & time efficiency).
"""

import io
import json
from typing import Any, Dict, List, Optional

# CRITICAL for macOS and headless server environments
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import database

# Palette definitions aligned with Expo / Vercel ultra-clean dark aesthetics
COLOR_BG = "#050507"          # pitch canvas
COLOR_PANEL = "#0c0c0e"       # clean dark card
COLOR_BORDER = "#1e1e24"      # micro border
COLOR_TEXT_PRIMARY = "#ffffff"# pure white
COLOR_TEXT_MUTED = "#94a3b8"  # slate-400
COLOR_GREEN = "#10b981"       # emerald-500 (Mastery >= 80%)
COLOR_BLUE = "#00f0ff"        # electric cyan (Proficient 65-79%)
COLOR_RED = "#ef4444"         # rose-500 (At-Risk < 65%)
COLOR_AMBER = "#f59e0b"       # amber-500 (Focus area)
COLOR_INDIGO = "#0070f3"      # azure blue (Trend fit)


def get_attempts_dataframe(attempts_list: Optional[List[Dict[str, Any]]] = None) -> pd.DataFrame:
    """
    Loads quiz attempts into a clean Pandas DataFrame, pulling from DB if not supplied.
    """
    if attempts_list is None:
        attempts_list = database.get_all_quiz_attempts(limit=100)

    if not attempts_list:
        return pd.DataFrame(
            columns=["id", "session_id", "created_at", "subject_category", "score_pct", "time_spent_sec", "weak_subtopics"]
        )

    df = pd.DataFrame(attempts_list)

    # Ensure required columns exist
    if "score_pct" in df.columns:
        df["score_pct"] = pd.to_numeric(df["score_pct"], errors="coerce").fillna(0.0)
    if "time_spent_sec" in df.columns:
        df["time_spent_sec"] = pd.to_numeric(df["time_spent_sec"], errors="coerce").fillna(0)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        df = df.sort_values(by="created_at", ascending=True).reset_index(drop=True)

    return df


def generate_telemetry_chart(attempts_list: Optional[List[Dict[str, Any]]] = None, view_mode: str = "mastery") -> bytes:
    """
    Renders a 2-panel dark-mode Matplotlib telemetry dashboard:
    - view_mode == 'mastery':
        Left: Horizontal Bar Chart of Average Mastery Score (%) by Subject Category
        Right: Rolling Retention & Score Progression Curve with confidence fill
    - view_mode == 'diagnostics':
        Left: Top Identified Weak Subtopics Frequency
        Right: Speed vs Accuracy Study Efficiency Scatter Quadrant
    Returns raw PNG bytes via io.BytesIO.
    """
    df = get_attempts_dataframe(attempts_list)

    fig, (ax_left, ax_right) = plt.subplots(
        nrows=1,
        ncols=2,
        figsize=(12.5, 4.2),
        dpi=140,
        facecolor=COLOR_BG
    )

    def style_axes(ax, title: str, xlabel: str = "", ylabel: str = ""):
        ax.set_facecolor(COLOR_PANEL)
        ax.set_title(title, color=COLOR_TEXT_PRIMARY, fontsize=12, fontweight="bold", pad=12, loc="left")
        if xlabel:
            ax.set_xlabel(xlabel, color=COLOR_TEXT_MUTED, fontsize=9, labelpad=8)
        if ylabel:
            ax.set_ylabel(ylabel, color=COLOR_TEXT_MUTED, fontsize=9, labelpad=8)
        ax.tick_params(colors=COLOR_TEXT_MUTED, labelsize=8.5, length=3)
        for spine in ax.spines.values():
            spine.set_color(COLOR_BORDER)
            spine.set_linewidth(1.0)
        ax.grid(color=COLOR_BORDER, linestyle="--", linewidth=0.7, alpha=0.7)

    if view_mode == "diagnostics":
        # -------------------------------------------------------------
        # DIAGNOSTICS VIEW: Left = Weak Subtopics Frequency
        # -------------------------------------------------------------
        style_axes(ax_left, "Weak-Spot Diagnostic Frequency", xlabel="Error Count across Attempts")
        
        # Aggregate weak subtopics
        weak_counts: Dict[str, int] = {}
        for row in df.itertuples():
            subtopics = getattr(row, "weak_subtopics", [])
            if isinstance(subtopics, str):
                try:
                    subtopics = json.loads(subtopics)
                except Exception:
                    subtopics = []
            for st in subtopics:
                if st:
                    weak_counts[st] = weak_counts.get(st, 0) + 1

        if weak_counts:
            sorted_weak = sorted(weak_counts.items(), key=lambda x: x[1], reverse=False)[-6:]
            st_names = [x[0] for x in sorted_weak]
            st_vals = [x[1] for x in sorted_weak]

            y_pos = np.arange(len(st_names))
            bars = ax_left.barh(y_pos, st_vals, color=COLOR_AMBER, height=0.55, edgecolor=COLOR_BORDER, linewidth=0.8, zorder=3)
            ax_left.set_yticks(y_pos)
            ax_left.set_yticklabels(st_names, color=COLOR_TEXT_PRIMARY, fontsize=8.5, fontweight="semibold")
            ax_left.set_xlim(0, max(st_vals) + 1.5)

            for bar, val in zip(bars, st_vals):
                ax_left.text(
                    val + 0.15,
                    bar.get_y() + bar.get_height() / 2,
                    f"{val} errors",
                    va="center",
                    ha="left",
                    color=COLOR_AMBER,
                    fontsize=8.5,
                    fontweight="bold"
                )
        else:
            ax_left.text(
                0.5, 0.5, "Zero Weak Subtopics Flagged! Flawless Retention.",
                color=COLOR_GREEN, ha="center", va="center", transform=ax_left.transAxes, fontsize=10
            )
            ax_left.set_xlim(0, 5)

        # -------------------------------------------------------------
        # DIAGNOSTICS VIEW: Right = Time Spent vs Score Efficiency Scatter
        # -------------------------------------------------------------
        style_axes(ax_right, "Study Pace vs Mastery Correlation", xlabel="Duration (Seconds)", ylabel="Score (%)")

        if not df.empty and len(df) >= 2:
            scores = df["score_pct"].values
            durations = df["time_spent_sec"].values

            # Scatter points color-coded by score tier
            point_colors = [COLOR_GREEN if s >= 80 else (COLOR_BLUE if s >= 65 else COLOR_RED) for s in scores]
            ax_right.scatter(durations, scores, c=point_colors, s=65, edgecolors="#ffffff", linewidth=0.8, alpha=0.85, zorder=4)

            # Trend line if possible
            if len(durations) > 2 and np.std(durations) > 0:
                z = np.polyfit(durations, scores, 1)
                p = np.poly1d(z)
                x_trend = np.linspace(min(durations), max(durations), 50)
                ax_right.plot(x_trend, p(x_trend), color=COLOR_INDIGO, linestyle="--", linewidth=1.5, alpha=0.8, label="Efficiency Fit", zorder=3)

            ax_right.axhline(80, color=COLOR_GREEN, linestyle=":", linewidth=1.2, alpha=0.85, zorder=2)
            ax_right.set_ylim(20, 105)
            ax_right.legend(loc="lower right", fontsize=8, facecolor=COLOR_BG, edgecolor=COLOR_BORDER, labelcolor=COLOR_TEXT_PRIMARY)
        else:
            ax_right.text(
                0.5, 0.5, "Collecting additional quiz telemetry points...",
                color=COLOR_TEXT_MUTED, ha="center", va="center", transform=ax_right.transAxes, fontsize=10
            )

    else:
        # -------------------------------------------------------------
        # MASTERY VIEW (Default): Left = Subject Mastery Bars
        # -------------------------------------------------------------
        style_axes(ax_left, "Subject Mastery Index (%)", xlabel="Score (%)")

        if not df.empty and "subject_category" in df.columns:
            subject_group = (
                df.groupby("subject_category")["score_pct"]
                .mean()
                .round(1)
                .sort_values(ascending=True)
            )

            categories = subject_group.index.tolist()
            scores = subject_group.values.tolist()

            bar_colors = [
                COLOR_GREEN if s >= 80 else (COLOR_BLUE if s >= 65 else COLOR_RED)
                for s in scores
            ]

            y_positions = np.arange(len(categories))
            bars = ax_left.barh(y_positions, scores, color=bar_colors, height=0.55, edgecolor=COLOR_BORDER, linewidth=0.8, zorder=3)

            ax_left.set_yticks(y_positions)
            ax_left.set_yticklabels(categories, color=COLOR_TEXT_PRIMARY, fontweight="semibold")
            ax_left.set_xlim(0, 105)

            # Benchmark line at 80% (Mastery threshold)
            ax_left.axvline(80, color=COLOR_GREEN, linestyle=":", linewidth=1.2, alpha=0.85, zorder=4)
            ax_left.text(80.5, len(categories) - 0.5, "80% Mastery", color=COLOR_GREEN, fontsize=7.5, va="bottom")

            for bar, score in zip(bars, scores):
                width = bar.get_width()
                ax_left.text(
                    width + 1.8,
                    bar.get_y() + bar.get_height() / 2,
                    f"{score:.1f}%",
                    va="center",
                    ha="left",
                    color=COLOR_TEXT_PRIMARY,
                    fontsize=8.5,
                    fontweight="bold"
                )
        else:
            ax_left.text(
                0.5, 0.5, "No Quiz Attempts Recorded Yet",
                color=COLOR_TEXT_MUTED, ha="center", va="center", transform=ax_left.transAxes, fontsize=10
            )
            ax_left.set_xlim(0, 100)

        # -------------------------------------------------------------
        # MASTERY VIEW: Right = Retention & Score Progression Curve
        # -------------------------------------------------------------
        style_axes(ax_right, "Retention & Score Progression Curve", xlabel="Quiz Attempt Sequence", ylabel="Score (%)")

        if not df.empty and len(df) >= 1:
            prog_df = df.tail(15).copy().reset_index(drop=True)
            x_indices = np.arange(1, len(prog_df) + 1)
            scores = prog_df["score_pct"].values

            rolling_series = prog_df["score_pct"].rolling(window=min(3, len(prog_df)), min_periods=1).mean()
            rolling_scores = rolling_series.values

            rolling_std = prog_df["score_pct"].rolling(window=min(3, len(prog_df)), min_periods=1).std().fillna(5.0).values
            upper_bound = np.clip(rolling_scores + rolling_std, 0, 100)
            lower_bound = np.clip(rolling_scores - rolling_std, 0, 100)

            ax_right.fill_between(
                x_indices,
                lower_bound,
                upper_bound,
                color=COLOR_BLUE,
                alpha=0.15,
                label="Retention Confidence Band",
                zorder=2
            )

            ax_right.plot(
                x_indices,
                scores,
                color=COLOR_TEXT_MUTED,
                linestyle="--",
                linewidth=1.0,
                marker="o",
                markersize=4.5,
                markerfacecolor=COLOR_PANEL,
                markeredgecolor=COLOR_BLUE,
                alpha=0.6,
                label="Raw Attempt Score",
                zorder=3
            )

            ax_right.plot(
                x_indices,
                rolling_scores,
                color=COLOR_BLUE,
                linewidth=2.2,
                marker="o",
                markersize=5.5,
                markerfacecolor=COLOR_BLUE,
                markeredgecolor="#ffffff",
                label="Rolling Retention Trend (k=3)",
                zorder=4
            )

            ax_right.axhline(80, color=COLOR_GREEN, linestyle=":", linewidth=1.2, alpha=0.85, zorder=3)
            ax_right.text(
                x_indices[-1] + 0.1, 80, "80% Target",
                color=COLOR_GREEN, fontsize=7.5, va="center"
            )

            ax_right.set_xticks(x_indices)
            ax_right.set_xticklabels([f"Q{i}" for i in x_indices])
            ax_right.set_ylim(20, 105)

            leg = ax_right.legend(
                loc="lower right",
                fontsize=7.5,
                facecolor=COLOR_BG,
                edgecolor=COLOR_BORDER,
                labelcolor=COLOR_TEXT_PRIMARY,
                framealpha=0.9
            )
            leg.get_frame().set_linewidth(0.8)
        else:
            ax_right.text(
                0.5, 0.5, "Awaiting Quiz Attempts for Trend Telemetry",
                color=COLOR_TEXT_MUTED, ha="center", va="center", transform=ax_right.transAxes, fontsize=10
            )
            ax_right.set_ylim(0, 100)

    plt.tight_layout(pad=2.0)

    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=140,
        bbox_inches="tight",
        facecolor=fig.get_facecolor(),
        edgecolor="none"
    )
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


if __name__ == "__main__":
    png1 = generate_telemetry_chart(view_mode="mastery")
    print(f"Mastery chart generated: {len(png1)} bytes")
    png2 = generate_telemetry_chart(view_mode="diagnostics")
    print(f"Diagnostics chart generated: {len(png2)} bytes")
