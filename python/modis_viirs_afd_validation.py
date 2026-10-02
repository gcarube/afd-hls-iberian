"""
AFD-S2 VALIDATION: MEDITERRANEAN vs IBERIAN against MODIS / VIIRS
4 validation fires — contextual categorisation + precision/recall vs VIIRS
(thesis Section 3.3.2, Tables 4.5 and 4.6, Fig. 4.4)

Python port of gee/scripts/modis_viirs_afd_validation.js, extended from one
selected fire to the 4 validation fires. Reads the HLS scenes from
data/hls_imagery/, the Iberian coefficients from
data/results/coefficients/coefficients_by_n.csv and the reference fire masks
that the GEE script exports for each fire (download them from
Drive/TFM_validation into data/modis_viirs/):

    <fire>_MODIS_active.tif   MODIS Terra + Aqua, FireMask 7-9    (EPSG:4326, 1 km)
    <fire>_VIIRS_active.tif   VIIRS Suomi NPP + NOAA-20, Bright_ti4 > 330 K (EPSG:4326, 375 m)

The reference time windows are set per fire in the GEE script. GEE only
exports a product when it has detections in the AOI, so a missing file means
"no detections" (VIIRS: LANCE archive gap for every fire before 2025).

The masks are resampled to the HLS grid with nearest neighbour, so an HLS
pixel is confirmed when it falls inside a reference fire pixel:
    CAT 1: inside a MODIS AND a VIIRS fire pixel   (highest confidence)
    CAT 2: inside a fire pixel of only one of them (intermediate confidence)
    CAT 3: confirmed by neither                    (false positive candidate)
    Confirmation rate = (CAT 1 + CAT 2) / (CAT 1 + CAT 2 + CAT 3)
    Precision vs VIIRS = area(AFD ∩ VIIRS) / area(AFD)
    Recall vs VIIRS    = area(AFD ∩ VIIRS) / area(VIIRS, native 375 m grid)

Difference with the GEE script: there, pixels without a VIIRS detection are
masked (not 0) when VIIRS has data, so they drop out of every category and
CAT 1 + CAT 2 + CAT 3 < total (Gargantilla in Table 4.5). Here they count as
"not confirmed by VIIRS", so the three categories always add up to the total.
Areas are computed on the WGS84 ellipsoid (see python/geodesy.py).

Usage:
    python python/modis_viirs_afd_validation.py               # CSV in data/results/validation/ and maps in data/results/figures/validation/
    python python/modis_viirs_afd_validation.py --no-maps     # CSV only
    python python/modis_viirs_afd_validation.py --coef-n 15   # use the mean coefficients of another N as the Iberian version
    python python/modis_viirs_afd_validation.py --ref-dir other_folder  # custom folder with the MODIS/VIIRS GeoTIFFs
"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from rasterio.warp import Resampling, reproject

from coefficients import DEFAULT_DATA_DIR, read_bands
from geodesy import mask_area_ha, pixel_area_m2
from jaccard import COEF_MED, DEFAULT_COEF_CSV, apply_afd, load_iberian_coefficients
from paths import FIG_VALIDATION_DIR, REFERENCE_DIR, VALIDATION_CSV
from scatter_validation import VALIDATION_FIRES

CSV_COLUMNS = ["name", "version", "modis_available", "viirs_available",
               "pix_total", "pix_cat1", "pix_cat2", "pix_cat3",
               "ha_total", "ha_cat1", "ha_cat2", "ha_cat3", "confirmation_rate",
               "ha_modis", "ha_viirs", "ha_inter_viirs", "precision_viirs", "recall_viirs"]

# Map colors (as in Fig. 4.4 of the thesis)
COLOR_ONLY_MED = (0.55, 0.0, 0.75)   # purple: Mediterranean only
COLOR_ONLY_IB = (0.0, 0.85, 0.95)    # cyan: Iberian only
COLOR_BOTH = (0.9, 0.0, 0.0)         # red: both versions
COLOR_MODIS = "orange"
COLOR_VIIRS = "yellow"


# ============================================
# READ: one reference fire mask
# ============================================
def read_reference(path, hls_path):
    """Return (mask on the HLS grid, area in ha on the native grid).

    Masked/nodata pixels and 0 are "no fire". A missing file (GEE skips the
    export when the product has no detections) gives an empty mask and 0 ha.
    """
    with rasterio.open(hls_path) as hls:
        hls_shape, hls_transform, hls_crs = hls.shape, hls.transform, hls.crs

    if not path.exists():
        return np.zeros(hls_shape, dtype=bool), 0.0

    with rasterio.open(path) as ref:
        native = ref.read(1, masked=True).filled(0) > 0
        on_hls = np.zeros(hls_shape, dtype=np.uint8)
        reproject(source=native.astype(np.uint8), destination=on_hls,
                  src_transform=ref.transform, src_crs=ref.crs,
                  dst_transform=hls_transform, dst_crs=hls_crs,
                  resampling=Resampling.nearest)

    # Native-grid area, as GEE computes it at the product scale (1 km / 375 m)
    return on_hls > 0, mask_area_ha(native, pixel_area_m2(path))


# ============================================
# FUNCTION: categorisation + VIIRS metrics for one AFD-S2 mask
# ============================================
def pct(a, b):
    """Percentage a / b, NaN when b is 0."""
    return 100 * a / b if b > 0 else np.nan


def validate_mask(mask, modis, viirs, ha_viirs, row_area_m2):
    cat1 = mask & modis & viirs
    cat2 = mask & (modis ^ viirs)
    cat3 = mask & ~modis & ~viirs

    ha = {k: mask_area_ha(m, row_area_m2)
          for k, m in [("total", mask), ("cat1", cat1), ("cat2", cat2), ("cat3", cat3)]}
    ha_inter = mask_area_ha(mask & viirs, row_area_m2)
    viirs_available = ha_viirs > 0

    return {
        "pix_total": int(mask.sum()),
        "pix_cat1": int(cat1.sum()),
        "pix_cat2": int(cat2.sum()),
        "pix_cat3": int(cat3.sum()),
        "ha_total": round(ha["total"], 2),
        "ha_cat1": round(ha["cat1"], 2),
        "ha_cat2": round(ha["cat2"], 2),
        "ha_cat3": round(ha["cat3"], 2),
        "confirmation_rate": round(pct(ha["cat1"] + ha["cat2"],
                                       ha["cat1"] + ha["cat2"] + ha["cat3"]), 1),
        "ha_inter_viirs": round(ha_inter, 2),
        # Overlap metrics vs the combined VIIRS mask, only with VIIRS data
        "precision_viirs": round(pct(ha_inter, ha["total"]), 1) if viirs_available else np.nan,
        "recall_viirs": round(pct(ha_inter, ha_viirs), 1) if viirs_available else np.nan,
    }


# ============================================
# MAP VISUALIZATION (Fig. 4.4)
# ============================================
def save_validation_map(bands, mask_med, mask_ib, modis, viirs, title, out_path):
    """False-color background with the detections of both versions and the
    MODIS/VIIRS fire pixels outlined on top."""
    # False-color background composite: min 0, max 5000, gamma 1.3 (as in GEE)
    rgb = np.stack([bands["b6"], bands["b5"], bands["b3"]], axis=-1)
    rgb = np.clip(rgb / 5000, 0, 1) ** (1 / 1.3)
    rgb = np.nan_to_num(rgb, nan=1.0)  # masked pixels drawn white

    overlay = rgb.copy()
    overlay[mask_med & ~mask_ib] = COLOR_ONLY_MED
    overlay[mask_ib & ~mask_med] = COLOR_ONLY_IB
    overlay[mask_med & mask_ib] = COLOR_BOTH

    fig, ax = plt.subplots(figsize=(9, 7))
    ax.imshow(overlay, interpolation="nearest")
    handles = [Patch(color=COLOR_ONLY_MED, label="AFD-S2 Mediterranean only"),
               Patch(color=COLOR_ONLY_IB, label="AFD-S2 Iberian only"),
               Patch(color=COLOR_BOTH, label="Both versions")]

    # Reference fire pixels as outlines, so the HLS detections stay visible
    for ref, color, label in [(modis, COLOR_MODIS, "MODIS fire (1 km)"),
                              (viirs, COLOR_VIIRS, "VIIRS fire (375 m)")]:
        if ref.any():
            ax.contour(ref.astype(float), levels=[0.5], colors=color, linewidths=1.2)
            handles.append(Line2D([], [], color=color, lw=1.5, label=label))

    ax.set_title(title)
    ax.axis("off")
    ax.legend(handles=handles, loc="lower right", framealpha=0.9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


# ============================================
# MAIN ANALYSIS: 4 VALIDATION FIRES
# ============================================
def main():
    parser = argparse.ArgumentParser(description="AFD-S2 validation against MODIS/VIIRS")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                        help="Folder with the HLS GeoTIFFs (default: data/hls_imagery)")
    parser.add_argument("--ref-dir", type=Path, default=REFERENCE_DIR,
                        help="Folder with the <fire>_MODIS_active / <fire>_VIIRS_active "
                             "GeoTIFFs (default: data/modis_viirs)")
    parser.add_argument("--coef-csv", type=Path, default=DEFAULT_COEF_CSV,
                        help="CSV with the coefficients per N (default: data/results/coefficients/coefficients_by_n.csv)")
    parser.add_argument("--coef-n", type=int, default=20,
                        help="N whose mean coefficients are used as the Iberian version (default: 20)")
    parser.add_argument("--out", type=Path, default=VALIDATION_CSV,
                        help="Output CSV (default: data/results/validation/validation_per_fire.csv)")
    parser.add_argument("--fig-dir", type=Path, default=FIG_VALIDATION_DIR,
                        help="Folder for the validation maps (default: data/results/figures/validation/)")
    parser.add_argument("--no-maps", action="store_true",
                        help="Do not generate the validation maps")
    args = parser.parse_args()

    coef_ib = load_iberian_coefficients(args.coef_csv, args.coef_n)
    versions = [("Mediterranean", COEF_MED), ("Iberian", coef_ib)]

    print("═══════════════════════════════════════════════════════")
    print("   AFD-S2 VALIDATION vs MODIS / VIIRS — VALIDATION FIRES")
    print("═══════════════════════════════════════════════════════")
    print("CAT 1: MODIS and VIIRS | CAT 2: only one | CAT 3: neither")
    print()

    rows = []
    for fire in VALIDATION_FIRES:
        hls_path = Path(args.data_dir) / f"{fire['asset']}.tif"
        bands = read_bands(fire["asset"], args.data_dir)
        row_area_m2 = pixel_area_m2(hls_path)
        modis, ha_modis = read_reference(args.ref_dir / f"{fire['name']}_MODIS_active.tif", hls_path)
        viirs, ha_viirs = read_reference(args.ref_dir / f"{fire['name']}_VIIRS_active.tif", hls_path)

        notes = [f"no {name} detections" for name, ha in (("MODIS", ha_modis), ("VIIRS", ha_viirs)) if ha == 0]
        print(f"── {fire['name']}" + (f"  ({', '.join(notes)})" if notes else ""))
        print(f"   MODIS {ha_modis:.2f} ha | VIIRS {ha_viirs:.2f} ha")

        masks = {}
        for label, coef in versions:
            masks[label] = apply_afd(bands, coef)
            stats = validate_mask(masks[label], modis, viirs, ha_viirs, row_area_m2)
            rows.append({"name": fire["name"], "version": label,
                         "modis_available": ha_modis > 0, "viirs_available": ha_viirs > 0,
                         "ha_modis": round(ha_modis, 2), "ha_viirs": round(ha_viirs, 2),
                         **stats})

            line = (f"   {label:<13} total={stats['ha_total']:7.2f} ha | "
                    f"CAT1={stats['ha_cat1']:7.2f}  CAT2={stats['ha_cat2']:7.2f}  "
                    f"CAT3={stats['ha_cat3']:6.2f} | conf.={stats['confirmation_rate']:5.1f}%")
            if ha_viirs > 0:
                line += (f" | P={stats['precision_viirs']:.1f}%"
                         f"  R={stats['recall_viirs']:.1f}%")
            print(line)

        if not args.no_maps:
            args.fig_dir.mkdir(parents=True, exist_ok=True)
            *_, date, product = fire["asset"].split("_")
            title = (f"{fire['name'].replace('_', ' ')} — "
                     f"{date[6:8]}/{date[4:6]}/{date[0:4]} ({product})")
            save_validation_map(bands, masks["Mediterranean"], masks["Iberian"],
                                modis, viirs, title,
                                args.fig_dir / f"validation_map_{fire['name']}.png")

    # ============================================
    # EXPORT RESULTS AS CSV
    # ============================================
    args.out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows)[CSV_COLUMNS].to_csv(args.out, index=False)

    print()
    print(f"▶ CSV saved to {args.out}")
    if not args.no_maps:
        print(f"▶ Maps saved to {args.fig_dir}")


if __name__ == "__main__":
    main()
