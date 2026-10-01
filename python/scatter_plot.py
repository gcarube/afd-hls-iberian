"""
SCATTER PLOT: ρ_Red vs ρ_SWIR2 of the validation fires (Fig. 3.2)
AFD-S2 Mediterranean vs Iberian −3σ bands over the real HLS pixels

Reads the HLS scenes from data/hls_imagery/ and the Iberian coefficients from
data/results/coefficients/coefficients_by_n.csv (same inputs as python/scatter_validation.py)
and draws, for each fire:
  - the C1 boundary Red = a·SWIR2 + b of both AFD-S2 versions (−3σ band),
  - the C2 thresholds SWIR2 = d of both versions (dotted verticals),
  - fire pixels by detection category (Mediterranean only / Iberian only / both),
  - a random sample of the non-fire pixels as grey background.

Areas in the legend are geodesic (WGS84, see python/geodesy.py), not the
nominal 0.09 ha/pixel.

Usage:
    python python/scatter_plot.py                              # Sierra Bermeja -> data/results/figures/scatter/scatter_Red_SWIR2_Sierra_Bermeja.png
    python python/scatter_plot.py --fires Losacio Gargantilla  # other validation fires (space-separated names)
    python python/scatter_plot.py --all                        # the 4 validation fires
    python python/scatter_plot.py --coef-n 15                  # use the mean coefficients of another N as the Iberian version
    python python/scatter_plot.py --bg-sample 30000            # size of the grey background sample (default 15000)
    python python/scatter_plot.py --xmax 8500                  # crop the SWIR2 axis (default: fit every fire pixel)
    python python/scatter_plot.py --ymax 6000                  # custom upper limit of the Red axis (HLS scale)
    python python/scatter_plot.py --out-dir other_folder       # custom output folder
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from coefficients import DEFAULT_DATA_DIR, read_bands
from geodesy import mask_area_ha, pixel_area_m2
from jaccard import COEF_MED, DEFAULT_COEF_CSV, apply_afd, load_iberian_coefficients
from paths import FIG_SCATTER_DIR
from scatter_validation import VALIDATION_FIRES

DEFAULT_FIG_DIR = FIG_SCATTER_DIR

# Display names used in the figure title
DISPLAY_NAMES = {
    "Sierra_Bermeja": "Sierra Bermeja",
    "Losacio": "Losacio",
    "Vall_dEbo": "Vall d'Ebo",
    "Gargantilla": "Gargantilla",
}

COLOR_MED = "#1565c0"       # Mediterranean band / Med-only pixels
COLOR_IB = "#c62828"        # Iberian band / Ib-only pixels
COLOR_BOTH = "#ff7311"      # pixels detected by both versions
COLOR_BG = "#c8c8c8"        # non-fire background

SEED = 42


def fmt_int(n):
    """Integer with thousands separator (15000 -> 15,000)."""
    return f"{n:,}"


def fire_title(fire):
    """'<name> fire — dd/mm/yyyy (<product>)' from the asset name."""
    *_, date, product = fire["asset"].split("_")
    name = DISPLAY_NAMES.get(fire["name"], fire["name"].replace("_", " "))
    return f"{name} fire — {date[6:8]}/{date[4:6]}/{date[0:4]} ({product})"


# ============================================
# FIGURE: scatter of one fire
# ============================================
def plot_scatter(fire, data_dir, coef_ib, out_path, bg_sample, xlim, ylim):
    bands = read_bands(fire["asset"], data_dir)
    row_area_m2 = pixel_area_m2(Path(data_dir) / f"{fire['asset']}.tif")

    fire_med = apply_afd(bands, COEF_MED)
    fire_ib = apply_afd(bands, coef_ib)
    valid = ~np.isnan(bands["b3"]) & ~np.isnan(bands["b6"])

    only_med = fire_med & ~fire_ib
    only_ib = fire_ib & ~fire_med
    both = fire_med & fire_ib
    background = valid & ~fire_med & ~fire_ib

    red, swir2 = bands["b3"], bands["b6"]

    # Default SWIR2 limit: fit every fire pixel (saturated active fire reaches SWIR2 > 2.0)
    if xlim[1] is None:
        fire_any = fire_med | fire_ib
        x_top = np.nanmax(swir2[fire_any]) if fire_any.any() else 8500
        xlim = (xlim[0], float(np.ceil(x_top * 1.03 / 500) * 500))

    fig, ax = plt.subplots(figsize=(8.9, 6.9))

    # Grey background: random sample of non-fire pixels
    bg_idx = np.flatnonzero(background)
    n_bg = min(bg_sample, bg_idx.size)
    bg_idx = np.random.default_rng(SEED).choice(bg_idx, size=n_bg, replace=False)
    ax.scatter(swir2.ravel()[bg_idx], red.ravel()[bg_idx], s=2, color=COLOR_BG,
               alpha=0.5, linewidths=0, zorder=1,
               label=f"No fire (sample of {fmt_int(n_bg)} px)")

    # Fire pixels by detection category (empty categories are left out of the legend)
    categories = [
        (only_med, COLOR_MED, "Fire, Mediterranean only"),
        (only_ib, COLOR_IB, "Fire, Iberian only"),
        (both, COLOR_BOTH, "Fire, both versions"),
    ]
    for mask, color, label in categories:
        n_px = int(mask.sum())
        if n_px == 0:
            continue
        ha = mask_area_ha(mask, row_area_m2)
        ax.scatter(swir2[mask], red[mask], s=12, color=color, alpha=0.9,
                   linewidths=0, zorder=3, label=f"{label} ({fmt_int(n_px)} px, {ha:.1f} ha)")

    # C1 boundaries: Red = a·SWIR2 + b
    x_line = np.array(xlim, dtype=float)
    ax.plot(x_line, COEF_MED["a"] * x_line + COEF_MED["b"], "--", color=COLOR_MED,
            lw=2, zorder=4, label=r"$-3\sigma$ band AFD-S2 Mediterranean")
    ax.plot(x_line, coef_ib["a"] * x_line + coef_ib["b"], "-.", color=COLOR_IB,
            lw=2, zorder=4, label=r"$-3\sigma$ band AFD-S2 Iberian")

    # C2 thresholds: SWIR2 = d, labelled just above the plot area so the legend never hides them
    # (label of the lower one on its left, the higher on its right)
    d_lines = sorted([(COEF_MED["d"], COLOR_MED, r"$d_{Med}$"),
                      (coef_ib["d"], COLOR_IB, r"$d_{Ib}$")])
    for i, (d, color, label) in enumerate(d_lines):
        ax.axvline(d, color=color, ls=":", lw=1.2, alpha=0.7, zorder=2)
        ax.annotate(label, xy=(d, 1.0), xycoords=("data", "axes fraction"),
                    xytext=(-3 if i == 0 else 3, 2), textcoords="offset points",
                    color=color, fontsize=11, ha="right" if i == 0 else "left", va="bottom")

    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_xlabel(r"$\rho_{2.20}$ — SWIR2 (HLS scale, $\times10^4$)", fontsize=13)
    ax.set_ylabel(r"$\rho_{0.66}$ — Red (HLS scale, $\times10^4$)", fontsize=13)
    ax.set_title(fire_title(fire), fontsize=13, color="#444444", pad=18)
    ax.grid(alpha=0.25)
    ax.spines[["top", "right"]].set_visible(False)

    # Legend order: lines first, then fire categories, then background
    # (drawn order is background, categories, Med line, Ib line)
    handles, labels = ax.get_legend_handles_labels()
    n = len(handles)
    order = [n - 2, n - 1] + list(range(1, n - 2)) + [0]
    ax.legend([handles[i] for i in order], [labels[i] for i in order],
              loc="upper left", fontsize=10.5, framealpha=0.9, markerscale=1.5)

    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)

    return {
        "only_med": int(only_med.sum()),
        "only_ib": int(only_ib.sum()),
        "both": int(both.sum()),
        "background_sample": n_bg,
    }


def main():
    parser = argparse.ArgumentParser(description="Red vs SWIR2 scatter plot of the validation fires")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                        help="Folder with the HLS GeoTIFFs (default: data/hls_imagery)")
    parser.add_argument("--coef-csv", type=Path, default=DEFAULT_COEF_CSV,
                        help="CSV with the coefficients per N (default: data/results/coefficients/coefficients_by_n.csv)")
    parser.add_argument("--coef-n", type=int, default=20,
                        help="N whose mean coefficients are used as the Iberian version (default: 20)")
    parser.add_argument("--fires", nargs="+", default=["Sierra_Bermeja"],
                        help="Validation fires to plot (default: Sierra_Bermeja)")
    parser.add_argument("--all", action="store_true",
                        help="Plot the 4 validation fires")
    parser.add_argument("--bg-sample", type=int, default=15000,
                        help="Number of non-fire pixels drawn as background (default: 15000)")
    parser.add_argument("--xmax", type=float, default=None,
                        help="Upper limit of the SWIR2 axis (default: fit every fire pixel)")
    parser.add_argument("--ymax", type=float, default=5200,
                        help="Upper limit of the Red axis (default: 5200)")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_FIG_DIR,
                        help="Output folder (default: data/results/figures/scatter)")
    args = parser.parse_args()

    known = {f["name"] for f in VALIDATION_FIRES}
    if args.all:
        fires = VALIDATION_FIRES
    else:
        unknown = set(args.fires) - known
        if unknown:
            parser.error(f"unknown fires {sorted(unknown)}; choose from {sorted(known)}")
        fires = [f for f in VALIDATION_FIRES if f["name"] in args.fires]

    coef_ib = load_iberian_coefficients(args.coef_csv, args.coef_n)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"AFD-S2 Mediterranean: a={COEF_MED['a']}, b={COEF_MED['b']:.0f}, d={COEF_MED['d']:.0f}")
    print(f"AFD-S2 Iberian (N={args.coef_n}): a={coef_ib['a']:.4f}, b={coef_ib['b']:.2f}, "
          f"d={coef_ib['d']:.2f}")

    for fire in fires:
        out_path = args.out_dir / f"scatter_Red_SWIR2_{fire['name']}.png"
        counts = plot_scatter(fire, args.data_dir, coef_ib, out_path, args.bg_sample,
                              xlim=(-100, args.xmax), ylim=(-100, args.ymax))
        print(f"── {fire['name']}: Med only={counts['only_med']}, Ib only={counts['only_ib']}, "
              f"both={counts['both']}, background sample={counts['background_sample']}")
        print(f"   ▶ {out_path}")


if __name__ == "__main__":
    main()
