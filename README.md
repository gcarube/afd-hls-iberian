# AFD-HLS Iberian — Regional Calibration of an Active Fire Detection Algorithm for the Iberian Peninsula

Regional recalibration and validation of the **AFD-S2** active fire detection algorithm ([Hu et al., 2021](https://doi.org/10.3390/rs13234790)) for the Iberian Peninsula, using 30 m **Harmonized Landsat Sentinel-2 (HLS)** imagery, cross-validated against MODIS and VIIRS operational fire products, and complemented with near-continuous **Meteosat Third Generation (MTG) FRP** monitoring.

> Master's thesis — MSc in Disaster Management (Universidad Complutense de Madrid / Universidad Politécnica de Madrid), June 2026.
> Author: **Guillermo Carreño Úbeda** · Supervisor: Gonzalo Barderas Machado

---

## Motivation

Operational active fire products — MODIS (1 km) and VIIRS (375 m) — are too coarse to resolve fire fronts in the fragmented Mediterranean landscapes of the Iberian Peninsula. The HLS programme delivers 30 m reflectance with a 2–3 day combined revisit, opening the door to decametric-scale active fire detection.

The AFD-S2 algorithm was originally calibrated on a global Mediterranean-biome sample. This work tests the hypothesis that **those global coefficients are too permissive for Iberian conditions**, and derives a regionally calibrated version: **AFD-HLS Iberian**.

## Key results

| Result | Value |
|---|---|
| Slope coefficient difference vs. original | **−32.6 %** (a = 0.501 vs. a = 0.743) |
| Coefficient convergence | Stable from **N = 15** fires onwards (< 3.5 % variation N=18→20) |
| Unconfirmed detections, Sierra Bermeja | **48.7 % → 0.5 %** |
| Unconfirmed detections, Vall d'Ebo | **8.8 % → 0 %** |
| Precision vs. VIIRS (Gargantilla) | **99.4 %** |
| Demonstrable false positives, pre-fire scene (Terrenho, 9 Aug) | **19.89 ha → 0.27 ha (−98.6 %)** |
| Mean spatial agreement between versions (Jaccard, n=20) | **J = 0.844** |

The Mediterranean version detects **4.4× more exclusive pixels** than the Iberian version across the full sample — and the contextual validation shows most of those extra detections lack external confirmation, consistent with false positives over high-SWIR-reflectance summer surfaces.

### Calibrated coefficients

| Coefficient | AFD-S2 Mediterranean | AFD-HLS Iberian | Δ (%) |
|---|---|---|---|
| a (OLS slope) | 0.743 | **0.501** | −32.6 |
| b (OLS intercept −3σ) | −680 | **−808** | +18.8 |
| c (P99 SWIR1) | 4750 | **4239** | −10.8 |
| d (P99 SWIR2) | 3550 | **3506** | −1.2 |

*Values scaled by 1×10⁴ (HLS reflectance scale factor), except `a` which is dimensionless.*

---

## Data

- **HLS v2.0** (HLSS30 / HLSL30) — 30 m surface reflectance, Sentinel-2 MSI and Landsat-8/9 OLI harmonized
- **MODIS** MOD14A1 / MYD14A1 — 1 km active fire
- **VIIRS** SNPP & NOAA-20 (NASA LANCE C2) — 375 m active fire
- **MTG FCI FRP-PIXEL** (EUMETSAT LSA SAF) — ~10 min cadence, ~1–2 km, Fire Radiative Power in MW
- **EFFIS** — fire perimeter and date verification

### Study sample

20 large wildfires (>500 ha) across Spain (15) and Portugal (5), 2020–2025. Each fire is analysed over a 30×30 km AOI (bounding box of a 15 km buffer). 16 fires used for calibration, 4 held out for validation (Sierra Bermeja, Losacio, Vall d'Ebo, Gargantilla).

| # | Fire | Date | Country | Sensor | Role |
|---|---|---|---|---|---|
| 1 | Almonaster la Real | 2020-08-29 | ESP | HLSS30 | C |
| 2 | Navalacruz | 2021-08-15 | ESP | HLSL30 | C |
| 3 | Ribeira da Gafa | 2021-08-17 | POR | HLSS30 | C |
| 4 | Sierra Bermeja | 2021-09-09 | ESP | HLSL30 | **V** |
| 5 | Losacio | 2022-07-18 | ESP | HLSS30 | **V** |
| 6 | Ateca | 2022-07-19 | ESP | HLSL30 | C |
| 7 | Balteiro | 2022-08-05 | POR | HLSS30 | C |
| 8 | Vall d'Ebo | 2022-08-14 | ESP | HLSL30 | **V** |
| 9 | Bejís | 2022-08-18 | ESP | HLSS30 | C |
| 10 | Lecrín | 2022-09-10 | ESP | HLSS30 | C |
| 11 | Santa Coloma de Queralt | 2023-03-29 | ESP | HLSL30 | C |
| 12 | Pinofranqueado | 2023-05-19 | ESP | HLSS30 | C |
| 13 | São Teotónio | 2023-08-07 | POR | HLSS30 | C |
| 14 | Albergaria-a-Velha | 2024-09-18 | POR | HLSS30 | C |
| 15 | Terrenho | 2025-08-11 | POR | HLSS30 | C |
| 16 | Una de Quintana | 2025-08-11 | ESP | HLSS30 | C |
| 17 | Medeiros | 2025-08-16 | ESP | HLSS30 | C |
| 18 | Burón | 2025-08-17 | ESP | HLSL30 | C |
| 19 | Gargantilla | 2025-08-17 | ESP | HLSL30 | **V** |
| 20 | Cardoso | 2025-09-26 | POR | HLSS30 | C |

---

## Method

The AFD-S2 algorithm combines three criteria into a single active fire mask:

- **C1** — OLS regression of Red (ρ₀.₆₆) on SWIR2 (ρ₂.₂₀); pixels falling below the lower prediction band (−3σ) are fire candidates
- **C2** — SWIR2 threshold (99th percentile)
- **C3** — SWIR1 threshold with a disjunctive condition

Calibration procedure:

1. Compute `a`, `b`, `c`, `d` independently for each of the 16 calibration fires over its AOI
2. Run an incremental convergence analysis from N=10 to N=20 to verify coefficient stabilisation
3. Adopt the arithmetic mean as the final Iberian parameter set

Validation:

- **Spatial agreement** between versions via the Jaccard index over all 20 fires
- **Contextual categorisation** of HLS detections against MODIS/VIIRS (CAT 1: confirmed by both; CAT 2: confirmed by one; CAT 3: unconfirmed), given the 30 m vs. 375 m/1 km scale mismatch that makes pixel-to-pixel comparison uninformative
- **Precision/recall** vs. VIIRS where data are available

> ⚠️ VIIRS data in GEE come from the LANCE near-real-time collections, which are retained only for a limited period. Only Gargantilla (Aug 2025) had VIIRS coverage at the HLS acquisition dates; the other three validation fires were validated against MODIS only.

---

## Case study: Terrenho (August 2025)

Nine-day temporal reconstruction combining 6 HLS snapshots with 12,504 MTG FRP detections across 756 ten-minute slots.

- The fire's most intense phase (14–15 Aug: 9,334 FRP records, 1,937,852 MW accumulated) had **no HLS coverage at all** — geostationary FRP was the only source characterising the critical period
- Diurnal/nocturnal FRP ratio of **5,600×** on 15 August, quantifying sub-daily fire dynamics invisible to polar-orbiting sensors
- The 9 August pre-fire scene provides an unambiguous false-positive test: 19.89 ha detected by the Mediterranean version vs. 0.27 ha by the Iberian version, over a scene with no fire

---

## Repository structure

```
.
├── gee/
│   ├── GEE_CAL_coefficients.js      # OLS coefficient computation per fire
│   ├── GEE_01_med_vs_iberian.js     # Version comparison, Jaccard index
│   ├── GEE_02_modis_viirs.js        # Validation against MODIS/VIIRS
│   └── GEE_04_agreement_maps.js     # Spatial agreement map export
├── python/
│   ├── download_frp_lsasaf.py       # MTG FRP-PIXEL download (EUMETSAT REST API)
│   └── analyze_frp_timeseries.py    # FRP time series processing and plots
├── data/
│   ├── fires_sample.csv             # 20-fire sample with AOIs and metadata
│   └── coefficients_per_fire.csv    # Individual AFD-S2 coefficients
├── figures/
└── docs/
    └── TFM_GCU.pdf                  # Full thesis (Spanish)
```

## Requirements

- A [Google Earth Engine](https://earthengine.google.com/) account (JavaScript Code Editor)
- Python 3.10+ with `requests`, `pandas`, `matplotlib` for the FRP scripts
- An [EUMETSAT Data Store](https://data.eumetsat.int/) API key for FRP download

## Usage

```bash
# 1. Download MTG FRP data for the study period
python python/download_frp_lsasaf.py --start 2025-08-09 --end 2025-08-18 --aoi terrenho

# 2. Process and plot the FRP time series
python python/analyze_frp_timeseries.py --input data/frp_terrenho/
```

GEE scripts are run directly in the Code Editor. `GEE_CAL_coefficients.js` expects HLS scenes pre-uploaded as assets; it exports a CSV of per-fire coefficients.

---

## Limitations

- Coefficients `a` and `b` show high dispersion (CV 45.3 % and 73.8 %), driven by scene composition: partial cloud cover, water bodies within the AOI, burned fraction, and vegetation heterogeneity
- Two out-of-season fires (March and May) suggest seasonal calibration could be worthwhile for operational use
- Residual inter-sensor discrepancies persist despite HLS harmonisation (12.6 % area difference between HLSL30 and HLSS30 scenes 8 minutes apart over Terrenho)
- Subgroup calibration (by sensor, ecoregion, or vegetation type) would require substantially larger per-group samples

## References

- Hu, X. et al. (2021). *Sentinel-2 MSI data for active fire detection in major fire-prone biomes: A multi-criteria approach.* International Journal of Applied Earth Observation and Geoinformation.
- Schroeder, W. et al. (2016). *Active fire detection using Landsat-8/OLI data.* Remote Sensing of Environment.
- Gorelick, N. et al. (2017). *Google Earth Engine: Planetary-scale geospatial analysis for everyone.* Remote Sensing of Environment.
- San-Miguel-Ayanz, J. et al. (2012). *Comprehensive monitoring of wildfires in Europe: the European Forest Fire Information System (EFFIS).*

## Citation

```bibtex
@mastersthesis{carreno2026afdhls,
  author  = {Carreño Úbeda, Guillermo},
  title   = {Adaptación y validación del algoritmo AFD-S2 para la detección
             de fuego activo en la Península Ibérica mediante imágenes HLS
             y análisis multifuente},
  school  = {Universidad Complutense de Madrid},
  year    = {2026},
  type    = {Master's thesis},
  address = {Madrid, Spain}
}
```

## License

MIT — see [LICENSE](LICENSE).