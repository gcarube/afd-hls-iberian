"""
AFD-S2 COMPARISON: MEDITERRANEAN vs IBERIAN
20 fires — Jaccard + validation metrics

Python port of gee/scripts/jaccard.js. Reads the HLS scenes from
data/hls_imagery/ and the Iberian coefficients from data/results/coefficients/coefficients_by_n.csv
(produced by python/coefficients.py) instead of the hard-coded GEE values.

Area correction: the GEE script converts pixels to hectares with a fixed
0.09 ha/pixel (30×30 m). The scenes are on an EPSG:4326 grid whose pixels are
only ~22-24 m wide east-west at Iberian latitudes (~650-720 m²), so that
overestimates areas by ~25-38%. ha_med / ha_ib are therefore computed from the
true area of each pixel on the WGS84 ellipsoid (see python/geodesy.py). The
original values are kept as ha_med_nominal / ha_ib_nominal for comparison.

Usage:
    python python/jaccard.py              # CSV in data/results/jaccard/ and maps of the 4 validation fires in data/results/figures/jaccard/
    python python/jaccard.py --no-maps    # CSV only
    python python/jaccard.py --coef-n 15  # use the mean coefficients of another N as the Iberian version
    python python/jaccard.py --out other/path.csv  # custom output CSV path
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from coefficients import DEFAULT_DATA_DIR, read_bands
from geodesy import mask_area_ha, pixel_area_m2
from paths import COEF_BY_N_CSV, FIG_JACCARD_DIR, JACCARD_CSV

DEFAULT_COEF_CSV = COEF_BY_N_CSV
DEFAULT_OUT = JACCARD_CSV
DEFAULT_FIG_DIR = FIG_JACCARD_DIR

# Nominal area of one pixel in hectares (1 pixel = 30×30 m = 0.09 ha), as in the
# GEE script. Only used for the *_nominal columns: it overestimates the true area
PIXEL_HA_NOMINAL = 0.09

# ----- AFD-S2 MEDITERRANEAN COEFFICIENTS (Hu et al. 2021) -----
# Converted from reflectance (0-1) to HLS scale (×10000)
COEF_MED = {
    "a": 0.743,
    "b": -0.068 * 10000,        # -680
    "c": 0.475 * 10000,         # 4750 (C3: SWIR1 ≥ 0.475)
    "d": 0.355 * 10000,         # 3550 (C2: SWIR2 ≥ 0.355)
    "d_extreme": 1.0 * 10000,   # 10000 (C3 OR: SWIR2 ≥ 1.0)
}

# ----- 20 FIRES -----
ALL_FIRES = [
    {"name": "Almonaster_la_Real", "asset": "Almonaster_20200829_HLSS30",      "role": "C"},
    {"name": "Navalacruz",         "asset": "Navalacruz_20210815_HLSL30",      "role": "C"},
    {"name": "Ribeira_da_Gafa",    "asset": "Ribeira_da_Gafa_20210817_HLSS30", "role": "C"},
    {"name": "Sierra_Bermeja",     "asset": "Sierra_Bermeja_20210909_HLSL30",  "role": "V"},
    {"name": "Losacio",            "asset": "Losacio_20220718_HLSS30",         "role": "V"},
    {"name": "Ateca",              "asset": "Ateca_20220719_HLSL30",           "role": "C"},
    {"name": "Balteiro",           "asset": "Balteiro_20220805_HLSS30",        "role": "C"},
    {"name": "Vall_dEbo",          "asset": "Vall_dEbo_20220814_HLSL30",       "role": "V"},
    {"name": "Bejis",              "asset": "Bejis_20220818_HLSS30",           "role": "C"},
    {"name": "Lecrin",             "asset": "Lecrin_2022_20220910_HLSS30",     "role": "C"},
    {"name": "Santa_Coloma",       "asset": "Santa_Coloma_20230329_HLSL30",    "role": "C"},
    {"name": "Pinofranqueado",     "asset": "Pinofranqueado_20230519_HLSS30",  "role": "C"},
    {"name": "Sao_Tetonio",        "asset": "Sao_Tetonio_20230807_HLSS30",     "role": "C"},
    {"name": "Albergaria",         "asset": "Albergaria_20240918_HLSS30",      "role": "C"},
    {"name": "Terrenho",           "asset": "Terrenho_20250811_HLSS30",        "role": "C"},
    {"name": "Una_de_Quintana",    "asset": "Una_de_Quintana_20250811_HLSS30", "role": "C"},
    {"name": "Medeiros",           "asset": "Medeiros_20250816_HLSS30",        "role": "C"},
    {"name": "Buron",              "asset": "Buron_20250817_HLSL30",           "role": "C"},
    {"name": "Gargantilla",        "asset": "Gargantilla_20250817_HLSL30",     "role": "V"},
    {"name": "Cardoso",            "asset": "Cardoso_20250926_HLSS30",         "role": "C"},
]

CSV_COLUMNS = ["name", "role", "pix_med", "pix_ib", "pix_inter", "pix_union",
               "pix_only_med", "pix_only_ib", "jaccard", "ha_med", "ha_ib",
               "ha_med_nominal", "ha_ib_nominal"]


# ============================================
# Iberian coefficients from the per-N CSV
# ============================================
def load_iberian_coefficients(csv_path, n):
    """AFD-S2 Iberian coefficients: mean values for the given N."""
    df = pd.read_csv(csv_path)
    row = df.loc[df["N"] == n]
    if row.empty:
        raise ValueError(f"N={n} not found in {csv_path}")
    row = row.iloc[0]
    return {
        "a": row["a_mean"],
        "b": row["b_mean"],
        "c": row["c_mean"],
        "d": row["d_mean"],
        "d_extreme": 10000,
    }


# ============================================
# FUNCTION: build the AFD-S2 mask
# ============================================
def apply_afd(bands, coef):
    """Boolean active-fire mask. Masked (NaN) pixels are always False,
    which matches GEE's selfMask() + count() on masked inputs."""
    b3, b5, b6 = bands["b3"], bands["b5"], bands["b6"]

    with np.errstate(invalid="ignore"):
        # C1: Red < a * SWIR2 + b
        c1 = b3 < (b6 * coef["a"] + coef["b"])

        # C2: SWIR2 >= d
        c2 = b6 >= coef["d"]

        # C3: SWIR1 >= c  OR  SWIR2 >= 1.0 (10000 on HLS scale)
        c3 = (b5 >= coef["c"]) | (b6 >= coef["d_extreme"])

    # Final mask: C1 AND C2 AND C3
    return c1 & c2 & c3


# ============================================
# FUNCTION: compute Jaccard between two masks
# ============================================
def compute_jaccard(mask_med, mask_ib, row_area_m2):
    # Intersection: pixels detected by both
    intersection = mask_med & mask_ib
    # Union: pixels detected by at least one
    union = mask_med | mask_ib
    # Exclusive areas
    only_med = mask_med & ~mask_ib
    only_ib = mask_ib & ~mask_med

    pix_inter = int(intersection.sum())
    pix_union = int(union.sum())
    stats = {
        "pix_med": int(mask_med.sum()),
        "pix_ib": int(mask_ib.sum()),
        "pix_inter": pix_inter,
        "pix_union": pix_union,
        "pix_only_med": int(only_med.sum()),
        "pix_only_ib": int(only_ib.sum()),
        # Jaccard = intersection / union (undefined if neither version detects anything)
        "jaccard": pix_inter / pix_union if pix_union > 0 else np.nan,
    }
    # Areas in hectares: true pixel area on the WGS84 ellipsoid
    stats["ha_med"] = round(mask_area_ha(mask_med, row_area_m2), 2)
    stats["ha_ib"] = round(mask_area_ha(mask_ib, row_area_m2), 2)
    # Nominal areas as in the GEE script (0.09 ha/pixel), kept for comparison
    stats["ha_med_nominal"] = round(stats["pix_med"] * PIXEL_HA_NOMINAL, 2)
    stats["ha_ib_nominal"] = round(stats["pix_ib"] * PIXEL_HA_NOMINAL, 2)
    return stats, intersection, only_med, only_ib


# ============================================
# MAP VISUALIZATION
# ============================================
def save_comparison_map(bands, intersection, only_med, only_ib, title, out_path):
    """False-color background (SWIR2, SWIR1, Red) with the comparison layers on top."""
    # False-color background composite: min 0, max 5000, gamma 1.3 (as in GEE visualize)
    rgb = np.stack([bands["b6"], bands["b5"], bands["b3"]], axis=-1)
    rgb = np.clip(rgb / 5000, 0, 1) ** (1 / 1.3)
    rgb = np.nan_to_num(rgb, nan=1.0)  # masked pixels drawn white

    # Comparison layers
    overlay = rgb.copy()
    overlay[intersection] = (1.0, 0.65, 0.0)   # orange: common detections
    overlay[only_med] = (0.0, 0.0, 1.0)        # blue: Mediterranean only
    overlay[only_ib] = (1.0, 0.0, 0.0)         # red: Iberian only

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.imshow(overlay, interpolation="nearest")
    ax.set_title(title)
    ax.axis("off")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in ("orange", "blue", "red")]
    ax.legend(handles, ["Common", "Mediterranean only", "Iberian only"],
              loc="lower right", framealpha=0.9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


# ============================================
# MAIN ANALYSIS: 20 FIRES
# ============================================
def main():
    parser = argparse.ArgumentParser(description="AFD-S2 Mediterranean vs Iberian comparison (Jaccard)")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                        help="Folder with the HLS GeoTIFFs (default: data/hls_imagery)")
    parser.add_argument("--coef-csv", type=Path, default=DEFAULT_COEF_CSV,
                        help="CSV with the coefficients per N (default: data/results/coefficients/coefficients_by_n.csv)")
    parser.add_argument("--coef-n", type=int, default=20,
                        help="N whose mean coefficients are used as the Iberian version (default: 20)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="Output CSV (default: data/results/jaccard/jaccard_per_fire.csv)")
    parser.add_argument("--fig-dir", type=Path, default=DEFAULT_FIG_DIR,
                        help="Folder for the validation-fire comparison maps (default: data/results/figures/jaccard/)")
    parser.add_argument("--no-maps", action="store_true",
                        help="Do not save the comparison maps")
    args = parser.parse_args()

    coef_ib = load_iberian_coefficients(args.coef_csv, args.coef_n)

    print("═══════════════════════════════════════════════════════")
    print("   AFD-S2 COMPARISON: MEDITERRANEAN vs IBERIAN")
    print("   20 fires — Jaccard + exclusive areas")
    print("═══════════════════════════════════════════════════════")
    print()
    print("AFD-S2 Mediterranean coefficients (Hu et al. 2021):")
    print(f"  a={COEF_MED['a']}, b={COEF_MED['b']:.0f}, c={COEF_MED['c']:.0f}, d={COEF_MED['d']:.0f}")
    print()
    print(f"AFD-S2 Iberian coefficients (N={args.coef_n}, mean):")
    print(f"  a={coef_ib['a']:.4f}, b={coef_ib['b']:.2f}, c={coef_ib['c']:.2f}, d={coef_ib['d']:.2f}")
    print()

    if not args.no_maps:
        args.fig_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for fire in ALL_FIRES:
        bands = read_bands(fire["asset"], args.data_dir)
        row_area_m2 = pixel_area_m2(Path(args.data_dir) / f"{fire['asset']}.tif")

        mask_med = apply_afd(bands, COEF_MED)
        mask_ib = apply_afd(bands, coef_ib)
        stats, intersection, only_med, only_ib = compute_jaccard(mask_med, mask_ib, row_area_m2)
        rows.append({"name": fire["name"], "role": fire["role"], **stats})

        print("──────────────────────────────────────────────")
        print(f"[{fire['role']}] {fire['name']}")
        print("  Mediterranean pixels:", stats["pix_med"])
        print("  Iberian pixels:      ", stats["pix_ib"])
        print("  Intersection:        ", stats["pix_inter"])
        print("  Union:               ", stats["pix_union"])
        print("  Mediterranean only:  ", stats["pix_only_med"])
        print("  Iberian only:        ", stats["pix_only_ib"])
        print("  Jaccard Index:       ", f"{stats['jaccard']:.4f}")
        print("  Mediterranean area (ha):", f"{stats['ha_med']:.2f}",
              f"(nominal 0.09 ha/px: {stats['ha_med_nominal']:.2f})")
        print("  Iberian area (ha):      ", f"{stats['ha_ib']:.2f}",
              f"(nominal 0.09 ha/px: {stats['ha_ib_nominal']:.2f})")
        print()

        # Only map the 4 validation fires to avoid clutter
        if fire["role"] == "V" and not args.no_maps:
            save_comparison_map(bands, intersection, only_med, only_ib,
                                f"{fire['name']} — Mediterranean vs Iberian AFD-S2",
                                args.fig_dir / f"jaccard_map_{fire['name']}.png")

    print()
    print("═══════════════════════════════════════════════════════")
    print("   VISUALIZATION LEGEND (validation fires)")
    print("   Orange: common detections")
    print("   Blue:   AFD-S2 Mediterranean only")
    print("   Red:    AFD-S2 Iberian only")
    print("═══════════════════════════════════════════════════════")

    # ============================================
    # EXPORT RESULTS AS CSV
    # ============================================
    args.out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows)[CSV_COLUMNS].to_csv(args.out, index=False)
    print()
    print(f"▶ CSV saved to {args.out}")
    if not args.no_maps:
        print(f"▶ Validation-fire comparison maps saved to {args.fig_dir}")


if __name__ == "__main__":
    main()
