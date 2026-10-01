"""
TOTAL PIXEL COUNT PER FIRE
Counts valid pixels in the 30x30 km AOI for every HLS scene in the sample

Python port of gee/scripts/pixels_per_fire.js. Reads the HLS scenes from
data/hls_imagery/ instead of the GEE assets.

Areas are computed on the WGS84 ellipsoid (see python/geodesy.py). GEE's
geometry.area() uses a spherical Earth, so area_ha_aoi is ~0.1-0.3% larger
than the GEE export (the difference grows with latitude). The extra column
px_area_m2 is the mean true pixel area: ~650-720 m² instead of the nominal
900 m², which is why px_total exceeds px_theoretical in unmasked scenes.

Usage:
    python python/pixels_per_fire.py                                   # writes data/results/pixels/pixels_per_fire.csv
    python python/pixels_per_fire.py --out other/path.csv              # custom output CSV path
    python python/pixels_per_fire.py --data-dir data/hls_imagery       # custom folder with the HLS GeoTIFFs
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from coefficients import DEFAULT_DATA_DIR, read_bands
from geodesy import footprint_area_m2, pixel_area_m2
from paths import PIXELS_CSV

DEFAULT_OUT = PIXELS_CSV

# Nominal HLS pixel: 30x30 m = 900 m² (used for px_theoretical, as in GEE)
PIXEL_M2 = 900

ALL_FIRES = [
    {"name": "Almonaster la Real", "asset": "Almonaster_20200829_HLSS30"},
    {"name": "Navalacruz",         "asset": "Navalacruz_20210815_HLSL30"},
    {"name": "Ribeira da Gafa",    "asset": "Ribeira_da_Gafa_20210817_HLSS30"},
    {"name": "Sierra Bermeja",     "asset": "Sierra_Bermeja_20210909_HLSL30"},
    {"name": "Losacio",            "asset": "Losacio_20220718_HLSS30"},
    {"name": "Ateca",              "asset": "Ateca_20220719_HLSL30"},
    {"name": "Balteiro",           "asset": "Balteiro_20220805_HLSS30"},
    {"name": "Vall d'Ebo",         "asset": "Vall_dEbo_20220814_HLSL30"},
    {"name": "Bejís",              "asset": "Bejis_20220818_HLSS30"},
    {"name": "Lecrín",             "asset": "Lecrin_2022_20220910_HLSS30"},
    {"name": "Santa Coloma",       "asset": "Santa_Coloma_20230329_HLSL30"},
    {"name": "Pinofranqueado",     "asset": "Pinofranqueado_20230519_HLSS30"},
    {"name": "São Tetónio",        "asset": "Sao_Tetonio_20230807_HLSS30"},
    {"name": "Albergaria",         "asset": "Albergaria_20240918_HLSS30"},
    {"name": "Terrenho",           "asset": "Terrenho_20250811_HLSS30"},
    {"name": "Una de Quintana",    "asset": "Una_de_Quintana_20250811_HLSS30"},
    {"name": "Medeiros",           "asset": "Medeiros_20250816_HLSS30"},
    {"name": "Burón",              "asset": "Buron_20250817_HLSL30"},
    {"name": "Gargantilla",        "asset": "Gargantilla_20250817_HLSL30"},
    {"name": "Cardoso",            "asset": "Cardoso_20250926_HLSS30"},
]


# ============================================
# FUNCTION: count valid pixels in band b3
# ============================================
def count_pixels(fire, data_dir):
    bands = read_bands(fire["asset"], data_dir)

    # Valid pixels in b3 (Red): value >= 0 and not nodata (NaN compares as False)
    with np.errstate(invalid="ignore"):
        px_total = int((bands["b3"] >= 0).sum())

    # Total AOI area in hectares (WGS84 ellipsoid)
    path = Path(data_dir) / f"{fire['asset']}.tif"
    area_m2 = footprint_area_m2(path)

    return {
        "fire": fire["name"],
        "px_total": px_total,
        "area_ha_aoi": area_m2 / 10000,
        "px_theoretical": area_m2 / PIXEL_M2,
        # Mean true pixel area of the scene (m²)
        "px_area_m2": float(pixel_area_m2(path).mean()),
    }


def main():
    parser = argparse.ArgumentParser(description="Total valid pixel count per fire")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                        help="Folder with the HLS GeoTIFFs (default: data/hls_imagery)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="Output CSV (default: data/results/pixels/pixels_per_fire.csv)")
    args = parser.parse_args()

    # Process all fires
    results = pd.DataFrame([count_pixels(f, args.data_dir) for f in ALL_FIRES])

    # Show in the console
    print("=== TOTAL PIXELS PER FIRE ===")
    print(results.to_string(index=False, float_format=lambda v: f"{v:.2f}"))

    # Export to CSV
    args.out.parent.mkdir(parents=True, exist_ok=True)
    results.to_csv(args.out, index=False)

    # Compute cumulative total
    print()
    print("Cumulative total pixels (20 fires):", int(results["px_total"].sum()))
    print(f"\n▶ CSV saved to {args.out}")


if __name__ == "__main__":
    main()
