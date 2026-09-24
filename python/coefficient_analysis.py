"""
VISUALIZATION: AFD-S2 COEFFICIENT EVOLUTION
Trend charts for N=10 to N=20

Python port of gee/scripts/coeficient_analysis.js. Instead of the static
sensitivityData table, it reads the per-N coefficients produced by
python/coefficients.py (data/coefficients_by_n.csv).

Usage:
    python python/coefficient_analysis.py
    python python/coefficient_analysis.py --show           # also display the plot figures
    python python/coefficient_analysis.py --input data/coefficients_by_n.csv --fig-dir figures --show
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "data" / "coefficients_by_n.csv"
DEFAULT_FIG_DIR = REPO_ROOT / "figures"

X_LABEL = "N (sample size)"

# Same series colors as the GEE charts
COLOR_A = "#1f77b4"
COLOR_B = "#ff7f0e"
COLOR_C = "#2ca02c"
COLOR_D = "#d62728"


# ============================================
# HELPER: line chart of one or more series vs N
# ============================================
def line_chart(df, series, title, y_label, out_path, y_window=None,
               point_size=5, show_legend=True):
    """Draw one line per series and save the figure.

    series: list of (column, label, color, marker, scale_factor)
    y_window: (min, max) preferred view window; it is widened if the data
              falls outside it, so no point is ever clipped.
    """
    fig, ax = plt.subplots(figsize=(8, 4.5))
    all_values = []
    for column, label, color, marker, factor in series:
        values = df[column] * factor
        all_values.append(values)
        ax.plot(df["N"], values, color=color, marker=marker, linewidth=2,
                markersize=point_size + 2, label=label)
        # Direct label at the last point
        if show_legend:
            ax.annotate(label, (df["N"].iloc[-1], values.iloc[-1]),
                        xytext=(6, 0), textcoords="offset points",
                        va="center", fontsize=9, color="0.25")

    if y_window is not None:
        data_min = min(v.min() for v in all_values)
        data_max = max(v.max() for v in all_values)
        ax.set_ylim(min(y_window[0], data_min), max(y_window[1], data_max))

    ax.set_title(title)
    ax.set_xlabel(X_LABEL)
    ax.set_ylabel(y_label)
    ax.set_xticks(df["N"])
    ax.grid(True, color="0.9", linewidth=0.8)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if show_legend:
        ax.legend(frameon=False)
        ax.margins(x=0.08)

    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    return fig


def main():
    parser = argparse.ArgumentParser(description="AFD-S2 coefficient evolution charts (N=10 to N=20)")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help="CSV with the coefficients per N (default: data/coefficients_by_n.csv)")
    parser.add_argument("--fig-dir", type=Path, default=DEFAULT_FIG_DIR,
                        help="Folder where the PNG charts are saved (default: figures)")
    parser.add_argument("--show", action="store_true",
                        help="Show the charts interactively after saving them")
    args = parser.parse_args()

    # ----- SENSITIVITY DATA -----
    df = pd.read_csv(args.input).sort_values("N").reset_index(drop=True)
    args.fig_dir.mkdir(parents=True, exist_ok=True)

    print("═════════════════════════════════════════════════")
    print("   AFD-S2 COEFFICIENT EVOLUTION (N=10→20)")
    print("═════════════════════════════════════════════════")
    print()

    # ============================================
    # CHART 1: coefficient a
    # ============================================
    line_chart(df, [("a_mean", "a", COLOR_A, "o", 1)],
               "Coefficient a (OLS slope) vs N", "a (slope)",
               args.fig_dir / "coef_a_vs_n.png", y_window=(0.45, 0.60),
               show_legend=False)
    print("Coefficient a: decreasing trend, stabilizing around ~0.50")
    print()

    # ============================================
    # CHART 2: coefficient b
    # ============================================
    line_chart(df, [("b_mean", "b", COLOR_B, "o", 1)],
               "Coefficient b (-3σ) vs N", "b (intercept -3σ)",
               args.fig_dir / "coef_b_vs_n.png", y_window=(-1100, -750),
               show_legend=False)
    print("Coefficient b: less negative as N increases (greater stability)")
    print()

    # ============================================
    # CHART 3: coefficient c
    # ============================================
    line_chart(df, [("c_mean", "c", COLOR_C, "o", 1)],
               "Coefficient c (SWIR1 p99) vs N", "c (SWIR1 99th percentile)",
               args.fig_dir / "coef_c_vs_n.png", y_window=(4100, 4500),
               show_legend=False)
    c_range = (df["c_mean"].max() - df["c_mean"].min()) / df["c_mean"].mean() * 100
    print(f"Coefficient c: VERY STABLE - variation {c_range:.1f}% ✓")
    print()

    # ============================================
    # CHART 4: coefficient d
    # ============================================
    line_chart(df, [("d_mean", "d", COLOR_D, "o", 1)],
               "Coefficient d (SWIR2 p99) vs N", "d (SWIR2 99th percentile)",
               args.fig_dir / "coef_d_vs_n.png", y_window=(3200, 3700),
               show_legend=False)
    d_range = (df["d_mean"].max() - df["d_mean"].min()) / df["d_mean"].mean() * 100
    print(f"Coefficient d: stable ({d_range:.1f}% variation)")
    print()

    # ============================================
    # CHART 5: all mean coefficients
    # ============================================
    line_chart(df, [("a_mean", "a (×1000)", COLOR_A, "o", 1000),
                    ("c_mean", "c", COLOR_C, "s", 1),
                    ("d_mean", "d", COLOR_D, "^", 1)],
               "Coefficient evolution vs N (scaled)", "Coefficient value",
               args.fig_dir / "coef_all_vs_n.png", point_size=4)
    print("Comparison: c and d vary little, a fluctuates more")
    print()

    # ============================================
    # CHART 6: standard deviations
    # ============================================
    line_chart(df, [("a_std", "std(a) [×1000]", COLOR_A, "o", 1000),
                    ("b_std", "std(b)", COLOR_B, "s", 1),
                    ("c_std", "std(c)", COLOR_C, "^", 1),
                    ("d_std", "std(d)", COLOR_D, "D", 1)],
               "Standard deviation evolution vs N", "Standard deviation",
               args.fig_dir / "coef_std_vs_n.png", point_size=4)
    first, last = df.iloc[0], df.iloc[-1]
    std_change = {k: (last[f"{k}_std"] - first[f"{k}_std"]) / first[f"{k}_std"] * 100
                  for k in ["a", "b", "c", "d"]}
    print("Standard deviations: "
          + ", ".join(f"std({k}) changes {v:+.1f}%" for k, v in std_change.items()))
    print()

    # ============================================
    # CHART 7: coefficient of variation
    # ============================================
    # Compute CV
    df["CV_a"] = df["a_std"] / df["a_mean"] * 100
    df["CV_b"] = df["b_std"] / df["b_mean"].abs() * 100
    df["CV_c"] = df["c_std"] / df["c_mean"] * 100
    df["CV_d"] = df["d_std"] / df["d_mean"] * 100

    line_chart(df, [("CV_a", "CV(a)", COLOR_A, "o", 1),
                    ("CV_b", "CV(b)", COLOR_B, "s", 1),
                    ("CV_c", "CV(c)", COLOR_C, "^", 1),
                    ("CV_d", "CV(d)", COLOR_D, "D", 1)],
               "Coefficient of variation (CV = std/mean × 100%) vs N", "CV (%)",
               args.fig_dir / "coef_cv_vs_n.png", y_window=(0, 80), point_size=4)

    print(f"Charts saved to {args.fig_dir}")

    # Final values (largest N) for the conclusions
    last = df.iloc[-1]
    n_last = int(last["N"])

    print()
    print("═════════════════════════════════════════════════")
    print("   CONCLUSIONS")
    print("═════════════════════════════════════════════════")
    print()
    print("1. STABILITY BY COEFFICIENT:")
    print(f"   ✓ c (SWIR1 p99): VERY STABLE - CV ~{last['CV_c']:.0f}%")
    print(f"   ✓ d (SWIR2 p99): MODERATE - CV ~{last['CV_d']:.0f}%")
    print(f"   ⚠ a (slope): HIGH VARIABILITY - CV ~{last['CV_a']:.0f}%")
    print(f"   ⚠ b (intercept): VERY HIGH VARIABILITY - CV ~{last['CV_b']:.0f}%")
    print()
    print(f"2. EFFECT OF INCREASING N ({int(first['N'])}→{n_last}):")
    for k, v in std_change.items():
        if abs(v) < 1:
            trend = "practically unchanged"
        else:
            trend = "better stability" if v < 0 else "more dispersion"
        print(f"   - std({k}) changes {v:+.1f}% ({trend})")
    print("   - c and d stabilize with N>15")
    print()
    print("3. METHODOLOGICAL RECOMMENDATION:")
    print("   ✓ c and d can be used as FIXED THRESHOLDS")
    print("   ⚠ a and b must be RECALIBRATED per region/biome")
    print(f"   ✓ N={n_last} provides robust estimates")
    print("   ✓ Fixed validation is essential for comparability")
    print()
    print(f"4. FINAL RECOMMENDED COEFFICIENTS (N={n_last}):")
    print(f"   a = {last['a_mean']:.3f} ± {last['a_std']:.3f}  (CV = {last['CV_a']:.1f}%)")
    print(f"   b = {last['b_mean']:.0f} ± {last['b_std']:.0f}     (CV = {last['CV_b']:.1f}%)")
    print(f"   c = {last['c_mean']:.0f} ± {last['c_std']:.0f}     (CV = {last['CV_c']:.1f}%) ← MOST STABLE")
    print(f"   d = {last['d_mean']:.0f} ± {last['d_std']:.0f}    (CV = {last['CV_d']:.1f}%)")
    print()
    print("5. PRACTICAL IMPLICATIONS:")
    print("   - High variability in a and b suggests ecological/climatic")
    print("     differences between fires")
    print("   - c (SWIR1 p99) is the MOST reliable coefficient")
    print("   - Consider regional calibration where possible")
    print()

    # Largest step in std(d) between consecutive N
    d_std_step = df["d_std"].diff()
    i_jump = int(d_std_step.idxmax())
    n_before, n_after = int(df["N"][i_jump - 1]), int(df["N"][i_jump])
    d_before, d_after = df["d_std"][i_jump - 1], df["d_std"][i_jump]

    print("6. SWIR2 (d) SENSITIVITY TO ACTIVE FIRE PIXELS:")
    print(f"   - Largest std(d) jump: N={n_before}→{n_after} "
          f"({d_before:.0f} → {d_after:.0f}, {(d_after - d_before) / d_before * 100:+.0f}%)")
    print("   - The jump is also present in the original GEE data (961 → 1447),")
    print("     so it is not a Python/GEE numerical artifact")
    print("   - GEE vs Python per-fire p99 differences are ~±30 reflectance units")
    print("     (~0.3%): GEE's percentile reducer is histogram-based (approximate),")
    print("     numpy computes the exact percentile")
    print("   - Cause: Sao_Tetonio_20230807_HLSS30 enters calibration at N=17 with")
    print("     d ≈ 7600, driven by a large active fire front (~1% of the AOI,")
    print("     SWIR2 ≈ 12000 on fire pixels). When fire pixels exceed ~1% of")
    print("     the scene, the p99 falls inside the fire tail instead of the background")
    print("   - Scene-wide p99 thresholds therefore depend on fire size within the")
    print("     AOI; c may be affected too (Losacio, Bejis: >2% of pixels with SWIR2 > 5000)")
    print("   - 'c and d stabilize with N>15' does not hold for d: c is stable,")
    print("     d is sensitive to scenes with extensive active fire")
    print("   - Possible refinements:")
    print("       · test how d and std(d) change when excluding Sao_Tetonio")
    print()
    print("═════════════════════════════════════════════════")

    if args.show:
        plt.show()


if __name__ == "__main__":
    main()
