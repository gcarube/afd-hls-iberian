"""
OUTPUT LAYOUT OF THE REPOSITORY
Single place for the default input/output folders of every script

    data/
    ├── hls_imagery/              HLS GeoTIFFs exported from GEE (input)
    ├── modis_viirs/              <fire>_MODIS_active.tif / <fire>_VIIRS_active.tif exported from GEE (input)
    └── results/
        ├── coefficients/         coefficients_by_n.csv, coefficients_per_fire.csv
        ├── jaccard/              jaccard_per_fire.csv
        ├── pixels/               pixels_per_fire.csv
        ├── scatter/              scatter_Red_SWIR2_<fire>.csv
        ├── validation/           validation_per_fire.csv
        └── figures/
            ├── coefficients/     coef_*_vs_n.png
            ├── jaccard/          jaccard_map_<fire>.png
            ├── scatter/          scatter_Red_SWIR2_<fire>.png
            └── validation/       validation_map_<fire>.png

Usage (as a module):
    from paths import COEF_BY_N_CSV, FIG_SCATTER_DIR
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
HLS_DIR = DATA_DIR / "hls_imagery"
REFERENCE_DIR = DATA_DIR / "modis_viirs"

# ----- CSV RESULTS -----
RESULTS_DIR = DATA_DIR / "results"
COEF_DIR = RESULTS_DIR / "coefficients"
JACCARD_DIR = RESULTS_DIR / "jaccard"
PIXELS_DIR = RESULTS_DIR / "pixels"
SCATTER_DIR = RESULTS_DIR / "scatter"
VALIDATION_DIR = RESULTS_DIR / "validation"

COEF_BY_N_CSV = COEF_DIR / "coefficients_by_n.csv"
COEF_PER_FIRE_CSV = COEF_DIR / "coefficients_per_fire.csv"
JACCARD_CSV = JACCARD_DIR / "jaccard_per_fire.csv"
PIXELS_CSV = PIXELS_DIR / "pixels_per_fire.csv"
VALIDATION_CSV = VALIDATION_DIR / "validation_per_fire.csv"

# ----- FIGURES -----
FIGURES_DIR = RESULTS_DIR / "figures"
FIG_COEF_DIR = FIGURES_DIR / "coefficients"
FIG_JACCARD_DIR = FIGURES_DIR / "jaccard"
FIG_SCATTER_DIR = FIGURES_DIR / "scatter"
FIG_VALIDATION_DIR = FIGURES_DIR / "validation"
