"""
REAL SCATTER PLOT DATA: validation fires
Exports a CSV per fire with ρ_Red vs ρ_SWIR2 and the AFD-S2 detection category
(data for Fig. 3.2)

Python port of gee/scripts/scatter_sierra_bermeja.js, extended from Sierra
Bermeja to the 4 validation fires (Sierra Bermeja, Losacio, Vall d'Ebo,
Gargantilla). Reads the HLS scenes from data/hls_imagery/ and the Iberian
coefficients from data/results/coefficients/coefficients_by_n.csv instead of the hard-coded
GEE values.

As in the GEE script (numPixels commented out), every valid pixel of the scene
is exported by default; masked pixels are dropped like ee.Image.sample() does.

Usage:
    python python/scatter_validation.py                          # all valid pixels, one CSV per fire in data/results/scatter/
    python python/scatter_validation.py --num-pixels 5000        # random sample of 5000 pixels per fire (seed 42)
    python python/scatter_validation.py --fires Sierra_Bermeja   # only some fires (space-separated names)
    python python/scatter_validation.py --coef-n 15              # use the mean coefficients of another N as the Iberian version
    python python/scatter_validation.py --out-dir other_folder   # custom output folder
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from coefficients import DEFAULT_DATA_DIR, read_bands
from jaccard import COEF_MED, DEFAULT_COEF_CSV, apply_afd, load_iberian_coefficients
from paths import SCATTER_DIR

DEFAULT_OUT_DIR = SCATTER_DIR

# ----- VALIDATION FIRES -----
VALIDATION_FIRES = [
    {"name": "Sierra_Bermeja", "asset": "Sierra_Bermeja_20210909_HLSL30"},
    {"name": "Losacio",        "asset": "Losacio_20220718_HLSS30"},
    {"name": "Vall_dEbo",      "asset": "Vall_dEbo_20220814_HLSL30"},
    {"name": "Gargantilla",    "asset": "Gargantilla_20250817_HLSL30"},
]

# Pixel category: 0=no fire, 1=Med only, 2=Ib only, 3=both
CATEGORY_LABELS = {0: "background", 1: "Med only", 2: "Ib only", 3: "both"}

SEED = 42


# ============================================
# FUNCTION: scatter table of one fire
# ============================================
def scatter_table(fire, data_dir, coef_ib, num_pixels=None):
    bands = read_bands(fire["asset"], data_dir)

    # Med and Ib fire masks
    fire_med = apply_afd(bands, COEF_MED)
    fire_ib = apply_afd(bands, coef_ib)

    # Pixel category: 0=no fire, 1=Med only, 2=Ib only, 3=both
    category = fire_med.astype(np.uint8) * 1 + fire_ib.astype(np.uint8) * 2

    # Keep only pixels valid in the exported bands (ee.Image.sample drops masked pixels)
    valid = ~np.isnan(bands["b3"]) & ~np.isnan(bands["b6"])
    df = pd.DataFrame({
        # Float exports carry rounding noise (e.g. 1554.9999999999998): HLS values are integers
        "b3": np.rint(bands["b3"][valid]).astype(np.int32),
        "b6": np.rint(bands["b6"][valid]).astype(np.int32),
        "category": category[valid],
    })

    # Optional random sample (equivalent to numPixels in GEE)
    if num_pixels is not None and num_pixels < len(df):
        df = df.sample(n=num_pixels, random_state=SEED).sort_index()

    return df


def main():
    parser = argparse.ArgumentParser(description="Red vs SWIR2 scatter data for the validation fires")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                        help="Folder with the HLS GeoTIFFs (default: data/hls_imagery)")
    parser.add_argument("--coef-csv", type=Path, default=DEFAULT_COEF_CSV,
                        help="CSV with the coefficients per N (default: data/results/coefficients/coefficients_by_n.csv)")
    parser.add_argument("--coef-n", type=int, default=20,
                        help="N whose mean coefficients are used as the Iberian version (default: 20)")
    parser.add_argument("--num-pixels", type=int, default=None,
                        help="Random sample size per fire (default: all valid pixels)")
    parser.add_argument("--fires", nargs="+", default=None,
                        help="Subset of fires to export (default: the 4 validation fires)")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                        help="Output folder (default: data/results/scatter)")
    args = parser.parse_args()

    fires = VALIDATION_FIRES
    if args.fires:
        known = {f["name"] for f in VALIDATION_FIRES}
        unknown = set(args.fires) - known
        if unknown:
            parser.error(f"unknown fires {sorted(unknown)}; choose from {sorted(known)}")
        fires = [f for f in VALIDATION_FIRES if f["name"] in args.fires]

    coef_ib = load_iberian_coefficients(args.coef_csv, args.coef_n)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("═══════════════════════════════════════════════════════")
    print("   RED vs SWIR2 SCATTER DATA — VALIDATION FIRES")
    print("═══════════════════════════════════════════════════════")
    print(f"AFD-S2 Mediterranean: a={COEF_MED['a']}, b={COEF_MED['b']:.0f}, "
          f"c={COEF_MED['c']:.0f}, d={COEF_MED['d']:.0f}")
    print(f"AFD-S2 Iberian (N={args.coef_n}): a={coef_ib['a']:.4f}, b={coef_ib['b']:.2f}, "
          f"c={coef_ib['c']:.2f}, d={coef_ib['d']:.2f}")
    print()

    for fire in fires:
        df = scatter_table(fire, args.data_dir, coef_ib, args.num_pixels)
        out_path = args.out_dir / f"scatter_Red_SWIR2_{fire['name']}.csv"
        df.to_csv(out_path, index=False)

        counts = df["category"].value_counts().reindex(CATEGORY_LABELS.keys(), fill_value=0)
        print(f"── {fire['name']}: {len(df)} pixels → {out_path.name}")
        for cat, label in CATEGORY_LABELS.items():
            print(f"     {cat} ({label}): {counts[cat]}")

    print()
    print("Columns: b3=Red, b6=SWIR2, category (0=bg, 1=MedOnly, 2=IbOnly, 3=both)")
    print(f"▶ CSVs saved to {args.out_dir}")


if __name__ == "__main__":
    main()
