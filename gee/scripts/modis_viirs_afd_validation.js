// ============================================
// AFD-S2 VALIDATION: MEDITERRANEAN vs IBERIAN
// Reference products: MODIS (Terra+Aqua) + VIIRS (Suomi+NOAA-20)
// Overlap analysis + contextual categorisation
// ============================================
//
// WARNING — MASKED VIIRS PIXELS:
// The LANCE VIIRS rasters only hold fire pixels, so when VIIRS has data the
// composite viirsActiveFire is masked everywhere else (not 0). In
// categorize() every HLS fire pixel outside a VIIRS fire pixel is then
// masked too and drops out of CAT 1/2/3: CAT 2 and CAT 3 come out as 0 and
// CAT 1 + CAT 2 + CAT 3 < total. This only affects fires with VIIRS data
// (Gargantilla); for the others the VIIRS composite is the constant 0 image.
// It matches Table 4.5 of the thesis (Gargantilla: total 96.24 ha, CAT 1
// 95.08 ha, CAT 2 = CAT 3 = 0). Use python/modis_viirs_afd_validation.py,
// which treats pixels without a VIIRS detection as "not confirmed by VIIRS".
//
// The exports *_MODIS_active and *_VIIRS_active are the input of the Python
// port: download them from Drive/TFM_validation into data/modis_viirs/.
// ============================================

// ----- AFD-S2 MEDITERRANEAN COEFFICIENTS (Hu et al. 2021) -----
// Converted from reflectance (0-1) to HLS scale (×10000)
var coef_med = {
  a: 0.743,
  b: -0.068 * 10000,        // -680
  c: 0.475 * 10000,         // 4750 (C3: SWIR1 ≥ c)
  d: 0.355 * 10000,         // 3550 (C2: SWIR2 ≥ d)
  d_extreme: 1.0 * 10000    // 10000 (C3 OR: SWIR2 ≥ 1.0)
};

// ----- AFD-S2 IBERIAN COEFFICIENTS (N=20, mean) -----
var coef_ib = {
  a: 0.5009,
  b: -808.17,
  c: 4238.57,
  d: 3505.90,
  d_extreme: 10000
};

// ----- VALIDATION FIRES -----
// Reference windows (end date exclusive):
//   VIIRS: the 2 days before the HLS date + the HLS date
//   MODIS: the day before the HLS date + the HLS date
var validationAssets = [
  {
    name: 'Sierra_Bermeja',
    path: 'projects/stunning-hull-476912-p8/assets/Sierra_Bermeja_20210909_HLSL30',
    date: '2021-09-09',
    viirsStart: '2021-09-07', viirsEnd: '2021-09-10',
    modisStart: '2021-09-08', modisEnd: '2021-09-10'
  },
  {
    name: 'Losacio',
    path: 'projects/stunning-hull-476912-p8/assets/Losacio_20220718_HLSS30',
    date: '2022-07-18',
    viirsStart: '2022-07-16', viirsEnd: '2022-07-19',
    modisStart: '2022-07-17', modisEnd: '2022-07-19'
  },
  {
    name: 'Vall_dEbo',
    path: 'projects/stunning-hull-476912-p8/assets/Vall_dEbo_20220814_HLSL30',
    date: '2022-08-14',
    viirsStart: '2022-08-12', viirsEnd: '2022-08-15',
    modisStart: '2022-08-13', modisEnd: '2022-08-15'
  },
  {
    name: 'Gargantilla',
    path: 'projects/stunning-hull-476912-p8/assets/Gargantilla_20250817_HLSL30',
    date: '2025-08-17',
    viirsStart: '2025-08-16', viirsEnd: '2025-08-18',
    modisStart: '2025-08-16', modisEnd: '2025-08-18'
  }
];

// ----- FIRE SELECTION -----
var selectedIndex = 0;  // 0=Sierra_Bermeja, 1=Losacio, 2=Vall_dEbo, 3=Gargantilla
var fireConfig = validationAssets[selectedIndex];

var SCALE = 30;

// ============================================
// FUNCTION: apply AFD-S2 with the given coefficients
// ============================================
function applyAFD_S2(img, coef) {
  var b3 = img.select('b3');  // Red
  var b5 = img.select('b5');  // SWIR1
  var b6 = img.select('b6');  // SWIR2

  // C1: Red < a · SWIR2 + b
  var c1 = b3.lt(b6.multiply(coef.a).add(coef.b));
  // C2: SWIR2 ≥ d
  var c2 = b6.gte(coef.d);
  // C3: SWIR1 ≥ c  OR  SWIR2 ≥ 1.0
  var c3 = b5.gte(coef.c).or(b6.gte(coef.d_extreme));

  return c1.and(c2).and(c3).rename('fire');
}

// ============================================
// PROCESS THE SELECTED FIRE
// ============================================

print('═════════════════════════════════════════════════');
print('   AFD-S2 VALIDATION: MEDITERRANEAN vs IBERIAN');
print('   Fire:', fireConfig.name);
print('   HLS date:', fireConfig.date);
print('═════════════════════════════════════════════════');
print('');

var img = ee.Image(fireConfig.path);
var geometry = img.geometry();

// Build the AFD-S2 masks
var fireMask_med = applyAFD_S2(img, coef_med);  // AFD-S2 Mediterranean
var fireMask_ib  = applyAFD_S2(img, coef_ib);   // AFD-S2 Iberian

// ============================================
// 1. MODIS TERRA (MOD14A1) - ACTIVE FIRE
// ============================================

print('──────────────────────────────────');
print('1. MODIS Terra MOD14A1 (Active Fire - 1km)');

var modisTerra = ee.ImageCollection('MODIS/061/MOD14A1')
  .filterDate(fireConfig.modisStart, fireConfig.modisEnd)
  .filterBounds(geometry);

var terraCount = modisTerra.size();
print('   Images found:', terraCount);

var terraFireBinary = ee.Image(0).rename('terra_fire');

if (terraCount.getInfo() > 0) {
  var terraFireMask = modisTerra.select('FireMask').max().clip(geometry);
  // FireMask 7=low, 8=nominal, 9=high confidence fire
  terraFireBinary = terraFireMask.gte(7).and(terraFireMask.lte(9)).rename('terra_fire');
  print('   ✓ Loaded with detections');
} else {
  print('   ⚠ No MODIS Terra data');
}

// ============================================
// 2. MODIS AQUA (MYD14A1) - ACTIVE FIRE
// ============================================

print('');
print('2. MODIS Aqua MYD14A1 (Active Fire - 1km)');

var modisAqua = ee.ImageCollection('MODIS/061/MYD14A1')
  .filterDate(fireConfig.modisStart, fireConfig.modisEnd)
  .filterBounds(geometry);

var aquaCount = modisAqua.size();
print('   Images found:', aquaCount);

var aquaFireBinary = ee.Image(0).rename('aqua_fire');

if (aquaCount.getInfo() > 0) {
  var aquaFireMask = modisAqua.select('FireMask').max().clip(geometry);
  aquaFireBinary = aquaFireMask.gte(7).and(aquaFireMask.lte(9)).rename('aqua_fire');
  print('   ✓ Loaded with detections');
} else {
  print('   ⚠ No MODIS Aqua data');
}

var modisActiveFire = terraFireBinary.or(aquaFireBinary).rename('modis_active');

// ============================================
// 3. VIIRS SUOMI NPP - ACTIVE FIRE
// ============================================

print('');
print('3. VIIRS Suomi NPP (Active Fire - 375m)');

var viirsSuomi = ee.ImageCollection('NASA/LANCE/SNPP_VIIRS/C2')
  .filterDate(fireConfig.viirsStart, fireConfig.viirsEnd)
  .filterBounds(geometry);

var suomiCount = viirsSuomi.size();
print('   Images found:', suomiCount);

var suomiFireBinary = ee.Image(0).rename('suomi_fire');
var suomiBright = ee.Image(0).rename('Bright_ti4');

if (suomiCount.getInfo() > 0) {
  suomiBright = viirsSuomi.select('Bright_ti4').max().clip(geometry);
  suomiFireBinary = suomiBright.gt(330).rename('suomi_fire');
  print('   ✓ Loaded with detections');
} else {
  print('   ⚠ No VIIRS Suomi data');
}

// ============================================
// 4. VIIRS NOAA-20 - ACTIVE FIRE
// ============================================

print('');
print('4. VIIRS NOAA-20 (Active Fire - 375m)');

var viirsNoaa = ee.ImageCollection('NASA/LANCE/NOAA20_VIIRS/C2')
  .filterDate(fireConfig.viirsStart, fireConfig.viirsEnd)
  .filterBounds(geometry);

var noaaCount = viirsNoaa.size();
print('   Images found:', noaaCount);

var noaaFireBinary = ee.Image(0).rename('noaa_fire');
var noaaBright = ee.Image(0).rename('Bright_ti4');

if (noaaCount.getInfo() > 0) {
  noaaBright = viirsNoaa.select('Bright_ti4').max().clip(geometry);
  noaaFireBinary = noaaBright.gt(330).rename('noaa_fire');
  print('   ✓ Loaded with detections');
} else {
  print('   ⚠ No VIIRS NOAA-20 data');
}

var viirsActiveFire = suomiFireBinary.or(noaaFireBinary).rename('viirs_active');

print('──────────────────────────────────');

// ============================================
// DETECTED AREAS
// ============================================

function areaHa(mask, scale, bandName) {
  var stats = mask.multiply(ee.Image.pixelArea()).reduceRegion({
    reducer: ee.Reducer.sum(),
    geometry: geometry,
    scale: scale,
    maxPixels: 1e9,
    bestEffort: true
  });
  return ee.Number(stats.get(bandName)).divide(10000);
}

var afdMedHa = areaHa(fireMask_med, SCALE, 'fire');
var afdIbHa  = areaHa(fireMask_ib,  SCALE, 'fire');
var modisActiveHa = areaHa(modisActiveFire, 1000, 'modis_active');
var viirsActiveHa = areaHa(viirsActiveFire, 375, 'viirs_active');

print('');
print('═════════════════════════════════════════════════');
print('   DETECTED AREAS');
print('═════════════════════════════════════════════════');
print('  AFD-S2 Mediterranean (HLS 30m):', afdMedHa.getInfo().toFixed(2), 'ha');
print('  AFD-S2 Iberian (HLS 30m):      ', afdIbHa.getInfo().toFixed(2), 'ha');
print('  MODIS Active Fire (1km):       ', modisActiveHa.getInfo().toFixed(2), 'ha');
print('  VIIRS Active Fire (375m):      ', viirsActiveHa.getInfo().toFixed(2), 'ha');

// ============================================
// CONTEXTUAL CATEGORISATION
// For EACH AFD-S2 version:
//   CAT 1: confirmed by both products (MODIS ∧ VIIRS)
//   CAT 2: confirmed by only one (MODIS ⊕ VIIRS)
//   CAT 3: not confirmed by the products
//   (CAT 4 — inside/outside the fire perimeter — is assessed in ArcGIS)
// ============================================

function categorize(afdMask, label) {
  // Reproject the references to 30 m for a pixel-to-pixel comparison
  // (an HLS pixel is confirmed when it falls inside a reference fire pixel)
  var modisAt30 = modisActiveFire.reproject({crs: 'EPSG:4326', scale: SCALE});
  var viirsAt30 = viirsActiveFire.reproject({crs: 'EPSG:4326', scale: SCALE});

  // CAT 1: confirmed by both
  var cat1 = afdMask.and(modisAt30).and(viirsAt30);
  // CAT 2: confirmed by only one
  var cat2 = afdMask.and(modisAt30.or(viirsAt30)).and(modisAt30.and(viirsAt30).not());
  // CAT 3: confirmed by neither
  var cat3 = afdMask.and(modisAt30.or(viirsAt30).not());

  var ha1 = areaHa(cat1, SCALE, 'fire');
  var ha2 = areaHa(cat2, SCALE, 'fire');
  var ha3 = areaHa(cat3, SCALE, 'fire');

  print('');
  print('  ── ' + label + ' ──');
  print('    CAT 1 (MODIS ∧ VIIRS):        ', ha1.getInfo().toFixed(2), 'ha');
  print('    CAT 2 (only one):             ', ha2.getInfo().toFixed(2), 'ha');
  print('    CAT 3 (neither):              ', ha3.getInfo().toFixed(2), 'ha');
  print('    Confirmation rate (CAT1+2):   ',
        ha1.add(ha2).divide(ha1.add(ha2).add(ha3)).multiply(100).getInfo().toFixed(1), '%');

  return {cat1: cat1, cat2: cat2, cat3: cat3, ha1: ha1, ha2: ha2, ha3: ha3};
}

print('');
print('═════════════════════════════════════════════════');
print('   CONTEXTUAL CATEGORISATION (vs MODIS + VIIRS)');
print('═════════════════════════════════════════════════');

var cats_med = categorize(fireMask_med, 'AFD-S2 MEDITERRANEAN');
var cats_ib  = categorize(fireMask_ib,  'AFD-S2 IBERIAN');

// ============================================
// OVERLAP METRICS vs VIIRS
// ============================================

print('');
print('═════════════════════════════════════════════════');
print('   METRICS vs VIIRS (primary reference)');
print('═════════════════════════════════════════════════');

if (viirsActiveHa.getInfo() > 0) {
  // Mediterranean
  var overlap_med_viirs = fireMask_med.and(viirsActiveFire);
  var overlapMedHa = areaHa(overlap_med_viirs, SCALE, 'fire');
  var precision_med = overlapMedHa.divide(afdMedHa).multiply(100);
  var recall_med = overlapMedHa.divide(viirsActiveHa).multiply(100);

  print('');
  print('  AFD-S2 Mediterranean:');
  print('    Intersection:', overlapMedHa.getInfo().toFixed(2), 'ha');
  print('    Precision:   ', precision_med.getInfo().toFixed(1), '%');
  print('    Recall:      ', recall_med.getInfo().toFixed(1), '%');

  // Iberian
  var overlap_ib_viirs = fireMask_ib.and(viirsActiveFire);
  var overlapIbHa = areaHa(overlap_ib_viirs, SCALE, 'fire');
  var precision_ib = overlapIbHa.divide(afdIbHa).multiply(100);
  var recall_ib = overlapIbHa.divide(viirsActiveHa).multiply(100);

  print('');
  print('  AFD-S2 Iberian:');
  print('    Intersection:', overlapIbHa.getInfo().toFixed(2), 'ha');
  print('    Precision:   ', precision_ib.getInfo().toFixed(1), '%');
  print('    Recall:      ', recall_ib.getInfo().toFixed(1), '%');
} else {
  print('   ⚠ No VIIRS data to compute the metrics');
}

// ============================================
// MAP VISUALIZATION
// ============================================

print('');
print('═════════════════════════════════════════════════');
print('   MAP LAYERS');
print('═════════════════════════════════════════════════');

Map.centerObject(geometry, 12);

// HLS true color and false color
Map.addLayer(img.select(['b4', 'b3', 'b2']), {min: 0, max: 4000, gamma: 1.2},
  '1. HLS True Color (RGB)', true);
Map.addLayer(img.select(['b6', 'b5', 'b3']), {min: 0, max: 5000, gamma: 1.2},
  '2. HLS False Color (SWIR2-SWIR1-Red)', false);

// MODIS active fire
if (modisActiveHa.getInfo() > 0) {
  Map.addLayer(modisActiveFire.selfMask(),
    {palette: ['FF6600'], min: 0, max: 1},
    '3. MODIS Active Fire (1km)', false, 0.5);
}

// Combined VIIRS
if (viirsActiveHa.getInfo() > 0) {
  Map.addLayer(viirsActiveFire.selfMask(),
    {palette: ['00FF00'], min: 0, max: 1},
    '4. Combined VIIRS (375m)', true, 0.6);
}

// AFD-S2 Mediterranean
Map.addLayer(fireMask_med.selfMask(),
  {palette: ['0066FF'], min: 0, max: 1},
  '5. AFD-S2 Mediterranean (30m)', true, 0.8);

// AFD-S2 Iberian
Map.addLayer(fireMask_ib.selfMask(),
  {palette: ['FF0000'], min: 0, max: 1},
  '6. AFD-S2 Iberian (30m)', true, 0.8);

// AFD-S2 Iberian categories (for visual analysis)
Map.addLayer(cats_ib.cat1.selfMask(),
  {palette: ['00FF00'], min: 0, max: 1},
  '7. CAT1 Ib: confirmed by both', false, 0.9);
Map.addLayer(cats_ib.cat2.selfMask(),
  {palette: ['FFFF00'], min: 0, max: 1},
  '8. CAT2 Ib: confirmed by one', false, 0.9);
Map.addLayer(cats_ib.cat3.selfMask(),
  {palette: ['FF00FF'], min: 0, max: 1},
  '9. CAT3 Ib: not confirmed', false, 0.9);

// AOI
Map.addLayer(geometry, {color: 'gray'}, 'AOI', false, 0.3);

print('');
print('COLOR CODES:');
print('  Blue:   AFD-S2 Mediterranean (30m)');
print('  Red:    AFD-S2 Iberian (30m)');
print('  Green:  Combined VIIRS (375m)');
print('  Orange: MODIS active fire (1km)');
print('');
print('CONTEXTUAL CATEGORIES (layers 7-9):');
print('  Green:   CAT1 - confirmed by MODIS and VIIRS');
print('  Yellow:  CAT2 - confirmed by only one');
print('  Magenta: CAT3 - not confirmed by the products');

// ============================================
// EXPORT DETECTIONS FOR ARCGIS
// ============================================

print('');
print('═════════════════════════════════════════════════');
print('   EXPORT TO DRIVE (for ArcGIS)');
print('═════════════════════════════════════════════════');
print('Run the pending tasks to download the GeoTIFFs:');

// HLS false color composite
Export.image.toDrive({
  image: img.select(['b6', 'b5', 'b3']).toFloat(),
  description: fireConfig.name + '_HLS_falseColor',
  fileNamePrefix: fireConfig.name + '_HLS_falseColor',
  region: geometry,
  scale: SCALE,
  crs: 'EPSG:4326',
  maxPixels: 1e9,
  folder: 'TFM_validation'
});

// AFD-S2 Mediterranean
Export.image.toDrive({
  image: fireMask_med.toByte(),
  description: fireConfig.name + '_AFDS2_Mediterranean',
  fileNamePrefix: fireConfig.name + '_AFDS2_Mediterranean',
  region: geometry,
  scale: SCALE,
  crs: 'EPSG:4326',
  maxPixels: 1e9,
  folder: 'TFM_validation'
});

// AFD-S2 Iberian
Export.image.toDrive({
  image: fireMask_ib.toByte(),
  description: fireConfig.name + '_AFDS2_Iberian',
  fileNamePrefix: fireConfig.name + '_AFDS2_Iberian',
  region: geometry,
  scale: SCALE,
  crs: 'EPSG:4326',
  maxPixels: 1e9,
  folder: 'TFM_validation'
});

// Combined MODIS (Terra + Aqua)
if (modisActiveHa.getInfo() > 0) {
  Export.image.toDrive({
    image: modisActiveFire.toByte(),
    description: fireConfig.name + '_MODIS_active',
    fileNamePrefix: fireConfig.name + '_MODIS_active',
    region: geometry,
    scale: 1000,
    crs: 'EPSG:4326',
    maxPixels: 1e9,
    folder: 'TFM_validation'
  });
}

// Combined VIIRS (Suomi + NOAA-20)
if (viirsActiveHa.getInfo() > 0) {
  Export.image.toDrive({
    image: viirsActiveFire.toByte(),
    description: fireConfig.name + '_VIIRS_active',
    fileNamePrefix: fireConfig.name + '_VIIRS_active',
    region: geometry,
    scale: 375,
    crs: 'EPSG:4326',
    maxPixels: 1e9,
    folder: 'TFM_validation'
  });
}

print('▶ Go to Tasks and run the exports. They are saved to Drive/TFM_validation');
print('');
print('═════════════════════════════════════════════════');
print('   END OF ANALYSIS');
print('═════════════════════════════════════════════════');
