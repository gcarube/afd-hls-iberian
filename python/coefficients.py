"""
AFD-S2 COEFFICIENT SENSITIVITY ANALYSIS
N=10 to N=20 with fixed validation set

Python port of gee/scripts/coeficients.js. Reads the HLS scenes exported
from GEE in data/hls_imagery/ instead of the GEE assets.

Usage:
    python python/coefficients.py
    python python/coefficients.py --data-dir data/hls_imagery --out data/coefficients_per_fire.csv

Always writes the mean/std coefficients for each N (10..20) to
data/coefficients_by_n.csv (override with --splits-out).
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "hls_imagery"
DEFAULT_SPLITS_OUT = REPO_ROOT / "data" / "coefficients_by_n.csv"

ALL_ASSETS = [
    "Albergaria_20240918_HLSS30",
    "Almonaster_20200829_HLSS30",
    "Ateca_20220719_HLSL30",
    "Balteiro_20220805_HLSS30",
    "Bejis_20220818_HLSS30",
    "Buron_20250817_HLSL30",
    "Cardoso_20250926_HLSS30",
    "Gargantilla_20250817_HLSL30",
    "Lecrin_2022_20220910_HLSS30",
    "Losacio_20220718_HLSS30",
    "Medeiros_20250816_HLSS30",
    "Navalacruz_20210815_HLSL30",
    "Pinofranqueado_20230519_HLSS30",
    "Ribeira_da_Gafa_20210817_HLSS30",
    "Santa_Coloma_20230329_HLSL30",
    "Sao_Tetonio_20230807_HLSS30",
    "Sierra_Bermeja_20210909_HLSL30",
    "Terrenho_20250811_HLSS30",
    "Una_de_Quintana_20250811_HLSS30",
    "Vall_dEbo_20220814_HLSL30",
]

# ----- FIXED VALIDATION -----
# N=10-11: 2 fires
VALIDATION2 = [
    "Sierra_Bermeja_20210909_HLSL30",
    "Losacio_20220718_HLSS30",
]

# N=12-17: 3 fires
VALIDATION3 = VALIDATION2 + ["Vall_dEbo_20220814_HLSL30"]

# N=18-20: 4 fires
VALIDATION4 = VALIDATION3 + ["Gargantilla_20250817_HLSL30"]

# Calibration pool (excludes the 4 validation fires) -> 16 assets available
CALIB_POOL = [a for a in ALL_ASSETS if a not in VALIDATION4]

# ----- SPLIT TABLE -----
SPLIT_TABLE = [
    {"total": 10, "calib": 8,  "valid_set": VALIDATION2},
    {"total": 11, "calib": 9,  "valid_set": VALIDATION2},
    {"total": 12, "calib": 9,  "valid_set": VALIDATION3},
    {"total": 13, "calib": 10, "valid_set": VALIDATION3},
    {"total": 14, "calib": 11, "valid_set": VALIDATION3},
    {"total": 15, "calib": 12, "valid_set": VALIDATION3},
    {"total": 16, "calib": 13, "valid_set": VALIDATION3},
    {"total": 17, "calib": 14, "valid_set": VALIDATION3},
    {"total": 18, "calib": 14, "valid_set": VALIDATION4},
    {"total": 19, "calib": 15, "valid_set": VALIDATION4},
    {"total": 20, "calib": 16, "valid_set": VALIDATION4},
]

# Band indices (1-based, rasterio) of the GEE export: b1..b6
# Surface reflectance scaled by 1e4. Native HLS band for each sensor:
#   band  name    HLSS30 (Sentinel-2 MSI)  HLSL30 (Landsat 8/9 OLI)  wavelength
#   b1    Blue    B2                       B2                        ~0.49 um
#   b2    Green   B3                       B3                        ~0.56 um
#   b3    Red     B4                       B4                        ~0.66 um
#   b4    NIR     B8A (narrow)             B5                        ~0.86 um
#   b5    SWIR1   B11                      B6                        ~1.61 um
#   b6    SWIR2   B12                      B7                        ~2.20 um
BAND_RED = 3    # b3: Red   (S30 B4  / L30 B4)
BAND_SWIR1 = 5  # b5: SWIR1 (S30 B11 / L30 B6)
BAND_SWIR2 = 6  # b6: SWIR2 (S30 B12 / L30 B7)


# ============================================
# READ: bands of one asset with its mask
# ============================================
def read_bands(asset_name, data_dir):
    """Return {band: float64 array with NaN on masked pixels}.

    GEE exports come in two formats:
      - float64: masked pixels are NaN.
      - int16 without nodata: masked pixels are 0 in every band.
    """
    path = Path(data_dir) / f"{asset_name}.tif"
    with rasterio.open(path) as src:
        data = src.read().astype("float64")
        is_int = np.issubdtype(np.dtype(src.dtypes[0]), np.integer)
        if src.nodata is not None:
            data[data == src.nodata] = np.nan

    if is_int:
        fill = (data == 0).all(axis=0)
        data[:, fill] = np.nan

    return {
        "b3": data[BAND_RED - 1],
        "b5": data[BAND_SWIR1 - 1],
        "b6": data[BAND_SWIR2 - 1],
    }


# ============================================
# FUNCTION: compute coefficients for ONE asset
# ============================================
def compute_coefficients(asset_name, data_dir):
    bands = read_bands(asset_name, data_dir)
    b3, b5, b6 = bands["b3"], bands["b5"], bands["b6"]

    # OLS regression: X = b6 (SWIR2), Y = b3 (Red)
    # (ee.Reducer.linearFit only uses pixels valid in both bands)
    valid = ~np.isnan(b3) & ~np.isnan(b6)
    x = b6[valid]
    y = b3[valid]
    a, b = np.polyfit(x, y, 1)

    # σ of the residuals
    # (ee.Reducer.stdDev is the population standard deviation -> ddof=0)
    residuals = y - (a * x + b)
    sigma = residuals.std(ddof=0)

    # b adjusted by -3σ (lower prediction bound)
    b_adjusted = b - 3 * sigma

    # 99th percentiles for c (SWIR1) and d (SWIR2), each band with its own mask
    c = np.nanpercentile(b5, 99)
    d = np.nanpercentile(b6, 99)

    return {
        "asset": asset_name,
        "a": a,
        "b": b_adjusted,
        "sigma": sigma,
        "c": c,
        "d": d,
    }


# ============================================
# FUNCTION: mean and std over a set of assets
# ============================================
def compute_mean_coefficients(asset_subset, coeffs_by_asset):
    df = pd.DataFrame([coeffs_by_asset[a] for a in asset_subset])
    result = {}
    for k in ["a", "b", "c", "d"]:
        result[f"{k}_mean"] = df[k].mean()
        result[f"{k}_std"] = df[k].std(ddof=0)  # ee.Reducer.stdDev -> population
    return result


# ============================================
# MAIN ANALYSIS
# ============================================
def main():
    parser = argparse.ArgumentParser(description="AFD-S2 coefficient sensitivity analysis")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR, type=Path,
                        help="Folder with the HLS GeoTIFFs (default: data/hls_imagery)")
    parser.add_argument("--out", type=Path, default=None,
                        help="Optional CSV path to save the individual coefficients")
    parser.add_argument("--splits-out", type=Path, default=DEFAULT_SPLITS_OUT,
                        help="CSV path for the mean/std coefficients per N "
                             "(default: data/coefficients_by_n.csv)")
    args = parser.parse_args()

    # Per-asset coefficients are computed once and reused
    coeffs_by_asset = {a: compute_coefficients(a, args.data_dir) for a in ALL_ASSETS}

    print("═════════════════════════════════════════════════")
    print("   AFD-S2 SENSITIVITY ANALYSIS (N=10 to N=20)")
    print("   Incremental fixed validation")
    print(f"   Calibration pool: {len(CALIB_POOL)} fires")
    print("═════════════════════════════════════════════════")
    print()
    print("FIXED VALIDATION:")
    print("  N=10-11: Sierra_Bermeja + Losacio")
    print("  N=12-17: + Vall_dEbo")
    print("  N=18-20: + Gargantilla")
    print()

    split_rows = []
    for split in SPLIT_TABLE:
        calib_assets = CALIB_POOL[: split["calib"]]
        valid_assets = split["valid_set"]

        print("══════════════════════════════════════════════")
        print(f"TOTAL={split['total']}  |  CALIBRATION={split['calib']}"
              f"  |  VALIDATION={len(valid_assets)}")
        print("══════════════════════════════════════════════")

        mc = compute_mean_coefficients(calib_assets, coeffs_by_asset)
        split_rows.append({"N": split["total"], **mc,
                           "n_calibration": len(calib_assets),
                           "n_validation": len(valid_assets)})

        print("  Mean coefficients (± std. dev.):")
        for k in ["a", "b", "c", "d"]:
            print(f"    {k}: {mc[f'{k}_mean']} ± {mc[f'{k}_std']}")
        print()

        print("  CALIBRATION fires:")
        for a in calib_assets:
            print("    [C]", a)
        print("  VALIDATION fires (fixed):")
        for a in valid_assets:
            print("    [V]", a)
        print()

    # ============================================
    # INDIVIDUAL COEFFICIENTS PER FIRE
    # ============================================
    print("═════════════════════════════════════════════════")
    print("   INDIVIDUAL COEFFICIENTS (20 FIRES)")
    print("═════════════════════════════════════════════════")
    print()

    for name in ALL_ASSETS:
        coeffs = coeffs_by_asset[name]
        role = "[VALIDATION]" if name in VALIDATION4 else "[calibration]"

        print("──────────────────────────────────")
        print(role, name)
        print("  a:      ", coeffs["a"])
        print("  b(-3σ): ", coeffs["b"])
        print("  σ:      ", coeffs["sigma"])
        print("  c(p99): ", coeffs["c"])
        print("  d(p99): ", coeffs["d"])
        print()

    print("═════════════════════════════════════════════════")
    print("   END OF ANALYSIS")
    print("═════════════════════════════════════════════════")
    print()
    print("Fixed validation fires:")
    print("  1. Sierra_Bermeja_20210909_HLSL30 (HLSL30, 2021)")
    print("  2. Losacio_20220718_HLSS30 (HLSS30, outlier)")
    print("  3. Vall_dEbo_20220814_HLSL30 (HLSL30, 2022)")
    print("  4. Gargantilla_20250817_HLSL30 (HLSL30, 2025)")

    calib_df = pd.DataFrame([coeffs_by_asset[a] for a in CALIB_POOL])
    print("Min/Max:")
    for k in ["a", "b", "c", "d"]:
        print(f"  {k}: {calib_df[k].min()} / {calib_df[k].max()}")

    # Columns: N, a_mean, a_std, b_mean, b_std, c_mean, c_std, d_mean, d_std,
    #          n_calibration, n_validation
    pd.DataFrame(split_rows).to_csv(args.splits_out, index=False)
    print(f"\nCoefficients per N saved to {args.splits_out}")

    if args.out is not None:
        out_df = pd.DataFrame([coeffs_by_asset[a] for a in ALL_ASSETS])
        out_df.insert(1, "role", ["V" if a in VALIDATION4 else "C" for a in ALL_ASSETS])
        out_df.to_csv(args.out, index=False)
        print(f"\nIndividual coefficients saved to {args.out}")


if __name__ == "__main__":
    main()
