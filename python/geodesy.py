"""
GEODESIC AREAS ON THE WGS84 ELLIPSOID
Shared helpers for the HLS scenes in data/hls_imagery/ (EPSG:4326 grid)

The scenes were exported from GEE in geographic coordinates with a pixel size
of ~0.000269°. That is ~30 m north-south but only ~22-24 m east-west at
Iberian latitudes, so a pixel covers ~650-720 m², not 900 m² (0.09 ha).
These helpers give the true area of every pixel on the WGS84 ellipsoid.

In an EPSG:4326 grid every cell is bounded by two parallels and two meridians,
so its area has a closed form (area of an ellipsoidal zone):

    A = a² · Δλ / 2 · (q(φ2) − q(φ1))
    q(φ) = (1 − e²) · [ sinφ / (1 − e² sin²φ) − 1/(2e) · ln((1 − e sinφ) / (1 + e sinφ)) ]

All pixels in a row share the same area, so the result is one value per row.

Usage (as a module):
    from geodesy import pixel_area_m2, footprint_area_m2
    row_area = pixel_area_m2(path)        # (rows,) area of one pixel in each row, m²
    total = footprint_area_m2(path)       # area of the whole raster extent, m²
"""

import numpy as np
import rasterio

# WGS84 ellipsoid
WGS84_A = 6378137.0
WGS84_F = 1 / 298.257223563
WGS84_E2 = WGS84_F * (2 - WGS84_F)
WGS84_E = np.sqrt(WGS84_E2)


def _q(lat_deg):
    """Authalic q(φ) term of the ellipsoidal zone area."""
    s = np.sin(np.radians(lat_deg))
    return (1 - WGS84_E2) * (
        s / (1 - WGS84_E2 * s ** 2)
        - 1 / (2 * WGS84_E) * np.log((1 - WGS84_E * s) / (1 + WGS84_E * s))
    )


def cell_area_m2(lat_south, lat_north, dlon_deg):
    """Area (m²) of a lat/lon cell on the WGS84 ellipsoid."""
    return WGS84_A ** 2 * np.radians(dlon_deg) / 2 * np.abs(_q(lat_north) - _q(lat_south))


def pixel_area_m2(path):
    """Area (m²) of one pixel for every row of an EPSG:4326 raster, shape (rows,)."""
    with rasterio.open(path) as src:
        if not src.crs.is_geographic:
            raise ValueError(f"{path} is not in geographic coordinates ({src.crs})")
        t = src.transform
        rows = np.arange(src.height)
    lat_top = t.f + rows * t.e           # t.e < 0: latitude decreases with row
    lat_bottom = lat_top + t.e
    return cell_area_m2(lat_bottom, lat_top, abs(t.a))


def footprint_area_m2(path):
    """Area (m²) of the whole raster extent on the WGS84 ellipsoid."""
    with rasterio.open(path) as src:
        left, bottom, right, top = src.bounds
    return float(cell_area_m2(bottom, top, right - left))


def mask_area_ha(mask, row_area_m2):
    """Area (ha) of the True pixels of a boolean mask, given the per-row pixel area."""
    return float((mask.sum(axis=1) * row_area_m2).sum() / 10000)
