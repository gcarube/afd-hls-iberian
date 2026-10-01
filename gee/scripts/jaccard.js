// ============================================
// AFD-S2 COMPARISON: MEDITERRANEAN vs IBERIAN
// 20 fires — Jaccard + validation metrics
// ============================================
//
// WARNING — AREA OVERESTIMATION:
// Hectares are computed with a fixed 0.09 ha/pixel (30×30 m). The assets are
// on an EPSG:4326 grid (~0.000269° pixels): ~30 m north-south but only
// ~22-24 m east-west at Iberian latitudes, i.e. ~650-720 m² per pixel.
// ha_med / ha_ib are therefore overestimated by ~25-38% (correction factor
// 0.73-0.80 depending on latitude). Pixel counts and Jaccard values are NOT
// affected. Use python/jaccard.py, which computes the true pixel area on the
// WGS84 ellipsoid (python/geodesy.py).
// ============================================

var SCALE = 30;

// ----- AFD-S2 MEDITERRANEAN COEFFICIENTS (Hu et al. 2021) -----
// Converted from reflectance (0-1) to HLS scale (×10000)
var coef_med = {
  a: 0.743,
  b: -0.068 * 10000,        // -680
  c: 0.475 * 10000,         // 4750 (C3: SWIR1 ≥ 0.475)
  d: 0.355 * 10000,         // 3550 (C2: SWIR2 ≥ 0.355)
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

// ----- 20 FIRES -----
var allFires = [
  {name: 'Almonaster_la_Real',    path: 'projects/stunning-hull-476912-p8/assets/Almonaster_20200829_HLSS30',         role: 'C'},
  {name: 'Navalacruz',            path: 'projects/stunning-hull-476912-p8/assets/Navalacruz_20210815_HLSL30',          role: 'C'},
  {name: 'Ribeira_da_Gafa',       path: 'projects/stunning-hull-476912-p8/assets/Ribeira_da_Gafa_20210817_HLSS30',    role: 'C'},
  {name: 'Sierra_Bermeja',        path: 'projects/stunning-hull-476912-p8/assets/Sierra_Bermeja_20210909_HLSL30',     role: 'V'},
  {name: 'Losacio',               path: 'projects/stunning-hull-476912-p8/assets/Losacio_20220718_HLSS30',            role: 'V'},
  {name: 'Ateca',                 path: 'projects/stunning-hull-476912-p8/assets/Ateca_20220719_HLSL30',              role: 'C'},
  {name: 'Balteiro',              path: 'projects/stunning-hull-476912-p8/assets/Balteiro_20220805_HLSS30',           role: 'C'},
  {name: 'Vall_dEbo',             path: 'projects/stunning-hull-476912-p8/assets/Vall_dEbo_20220814_HLSL30',          role: 'V'},
  {name: 'Bejis',                 path: 'projects/stunning-hull-476912-p8/assets/Bejis_20220818_HLSS30',              role: 'C'},
  {name: 'Lecrin',                path: 'projects/stunning-hull-476912-p8/assets/Lecrin_2022_20220910_HLSS30',         role: 'C'},
  {name: 'Santa_Coloma',          path: 'projects/stunning-hull-476912-p8/assets/Santa_Coloma_20230329_HLSL30',       role: 'C'},
  {name: 'Pinofranqueado',        path: 'projects/stunning-hull-476912-p8/assets/Pinofranqueado_20230519_HLSS30',     role: 'C'},
  {name: 'Sao_Tetonio',           path: 'projects/stunning-hull-476912-p8/assets/Sao_Tetonio_20230807_HLSS30',        role: 'C'},
  {name: 'Albergaria',            path: 'projects/stunning-hull-476912-p8/assets/Albergaria_20240918_HLSS30',         role: 'C'},
  {name: 'Terrenho',              path: 'projects/stunning-hull-476912-p8/assets/Terrenho_20250811_HLSS30',           role: 'C'},
  {name: 'Una_de_Quintana',       path: 'projects/stunning-hull-476912-p8/assets/Una_de_Quintana_20250811_HLSS30',    role: 'C'},
  {name: 'Medeiros',              path: 'projects/stunning-hull-476912-p8/assets/Medeiros_20250816_HLSS30',           role: 'C'},
  {name: 'Buron',                 path: 'projects/stunning-hull-476912-p8/assets/Buron_20250817_HLSL30',              role: 'C'},
  {name: 'Gargantilla',           path: 'projects/stunning-hull-476912-p8/assets/Gargantilla_20250817_HLSL30',        role: 'V'},
  {name: 'Cardoso',               path: 'projects/stunning-hull-476912-p8/assets/Cardoso_20250926_HLSS30',            role: 'C'}
];

// ============================================
// FUNCTION: build the AFD-S2 mask
// ============================================
function applyAFD(img, coef) {
  var b3 = img.select('b3');  // Red
  var b5 = img.select('b5');  // SWIR1
  var b6 = img.select('b6');  // SWIR2

  // C1: Red < a * SWIR2 + b
  var c1 = b3.lt(b6.multiply(coef.a).add(coef.b));

  // C2: SWIR2 >= d
  var c2 = b6.gte(coef.d);

  // C3: SWIR1 >= c  OR  SWIR2 >= 1.0 (10000 on HLS scale)
  var c3 = b5.gte(coef.c).or(b6.gte(coef.d_extreme));

  // Final mask: C1 AND C2 AND C3
  return c1.and(c2).and(c3).selfMask();
}

// ============================================
// FUNCTION: compute Jaccard between two masks
// ============================================
function computeJaccard(maskA, maskB, geometry) {
  // Intersection: pixels detected by both
  var intersection = maskA.and(maskB).selfMask();
  // Union: pixels detected by at least one
  var union = maskA.or(maskB).selfMask();

  var countIntersection = intersection.reduceRegion({
    reducer: ee.Reducer.count(),
    geometry: geometry,
    scale: SCALE,
    maxPixels: 1e9,
    bestEffort: true
  });

  var countUnion = union.reduceRegion({
    reducer: ee.Reducer.count(),
    geometry: geometry,
    scale: SCALE,
    maxPixels: 1e9,
    bestEffort: true
  });

  // Exclusive areas
  var onlyA = maskA.and(maskB.not()).selfMask();
  var onlyB = maskB.and(maskA.not()).selfMask();

  var countOnlyA = onlyA.reduceRegion({
    reducer: ee.Reducer.count(),
    geometry: geometry,
    scale: SCALE,
    maxPixels: 1e9,
    bestEffort: true
  });

  var countOnlyB = onlyB.reduceRegion({
    reducer: ee.Reducer.count(),
    geometry: geometry,
    scale: SCALE,
    maxPixels: 1e9,
    bestEffort: true
  });

  var countA = maskA.reduceRegion({
    reducer: ee.Reducer.count(),
    geometry: geometry,
    scale: SCALE,
    maxPixels: 1e9,
    bestEffort: true
  });

  var countB = maskB.reduceRegion({
    reducer: ee.Reducer.count(),
    geometry: geometry,
    scale: SCALE,
    maxPixels: 1e9,
    bestEffort: true
  });

  return {
    intersection: countIntersection,
    union: countUnion,
    onlyMed: countOnlyA,
    onlyIb: countOnlyB,
    totalMed: countA,
    totalIb: countB
  };
}

// ============================================
// MAIN ANALYSIS: 20 FIRES
// ============================================

print('═══════════════════════════════════════════════════════');
print('   AFD-S2 COMPARISON: MEDITERRANEAN vs IBERIAN');
print('   20 fires — Jaccard + exclusive areas');
print('═══════════════════════════════════════════════════════');
print('');
print('AFD-S2 Mediterranean coefficients (Hu et al. 2021):');
print('  a=' + coef_med.a + ', b=' + coef_med.b +
      ', c=' + coef_med.c + ', d=' + coef_med.d);
print('');
print('AFD-S2 Iberian coefficients (N=20, mean):');
print('  a=' + coef_ib.a + ', b=' + coef_ib.b +
      ', c=' + coef_ib.c + ', d=' + coef_ib.d);
print('');

allFires.forEach(function(fire) {
  var img = ee.Image(fire.path);
  var geometry = img.geometry();

  // Build masks (no selfMask, for boolean operations)
  var b3 = img.select('b3');
  var b5 = img.select('b5');
  var b6 = img.select('b6');

  // AFD-S2 Mediterranean
  var c1_med = b3.lt(b6.multiply(coef_med.a).add(coef_med.b));
  var c2_med = b6.gte(coef_med.d);
  var c3_med = b5.gte(coef_med.c).or(b6.gte(coef_med.d_extreme));
  var mask_med = c1_med.and(c2_med).and(c3_med);

  // AFD-S2 Iberian
  var c1_ib = b3.lt(b6.multiply(coef_ib.a).add(coef_ib.b));
  var c2_ib = b6.gte(coef_ib.d);
  var c3_ib = b5.gte(coef_ib.c).or(b6.gte(coef_ib.d_extreme));
  var mask_ib = c1_ib.and(c2_ib).and(c3_ib);

  // Jaccard and areas
  var intersection = mask_med.and(mask_ib);
  var union = mask_med.or(mask_ib);
  var onlyMed = mask_med.and(mask_ib.not());
  var onlyIb = mask_ib.and(mask_med.not());

  var stats = ee.Dictionary({
    pix_med: mask_med.selfMask().reduceRegion({
      reducer: ee.Reducer.count(), geometry: geometry,
      scale: SCALE, maxPixels: 1e9, bestEffort: true
    }).values().get(0),
    pix_ib: mask_ib.selfMask().reduceRegion({
      reducer: ee.Reducer.count(), geometry: geometry,
      scale: SCALE, maxPixels: 1e9, bestEffort: true
    }).values().get(0),
    pix_inter: intersection.selfMask().reduceRegion({
      reducer: ee.Reducer.count(), geometry: geometry,
      scale: SCALE, maxPixels: 1e9, bestEffort: true
    }).values().get(0),
    pix_union: union.selfMask().reduceRegion({
      reducer: ee.Reducer.count(), geometry: geometry,
      scale: SCALE, maxPixels: 1e9, bestEffort: true
    }).values().get(0),
    pix_only_med: onlyMed.selfMask().reduceRegion({
      reducer: ee.Reducer.count(), geometry: geometry,
      scale: SCALE, maxPixels: 1e9, bestEffort: true
    }).values().get(0),
    pix_only_ib: onlyIb.selfMask().reduceRegion({
      reducer: ee.Reducer.count(), geometry: geometry,
      scale: SCALE, maxPixels: 1e9, bestEffort: true
    }).values().get(0)
  });

  print('──────────────────────────────────────────────');
  print('[' + fire.role + '] ' + fire.name);
  print('  Mediterranean pixels:', stats.get('pix_med'));
  print('  Iberian pixels:      ', stats.get('pix_ib'));
  print('  Intersection:        ', stats.get('pix_inter'));
  print('  Union:               ', stats.get('pix_union'));
  print('  Mediterranean only:  ', stats.get('pix_only_med'));
  print('  Iberian only:        ', stats.get('pix_only_ib'));

  // Jaccard = intersection / union
  var jaccard = ee.Number(stats.get('pix_inter'))
    .divide(ee.Number(stats.get('pix_union')));
  print('  Jaccard Index:       ', jaccard);

  // Areas in hectares (1 pixel = 30×30 m = 0.09 ha)
  // WARNING: overestimated by ~25-38% on the EPSG:4326 grid (see header)
  var ha_med = ee.Number(stats.get('pix_med')).multiply(0.09);
  var ha_ib  = ee.Number(stats.get('pix_ib')).multiply(0.09);
  print('  Mediterranean area (ha):', ha_med);
  print('  Iberian area (ha):      ', ha_ib);
  print('');

  // ---- MAP VISUALIZATION ----
  // False-color background composite
  var falseColor = img.select(['b6', 'b5', 'b3']).visualize({
    min: 0, max: 5000, gamma: 1.3
  });

  // Comparison layers
  var commonVis = intersection.selfMask().visualize({palette: ['orange']});
  var onlyMedVis = onlyMed.selfMask().visualize({palette: ['blue']});
  var onlyIbVis = onlyIb.selfMask().visualize({palette: ['red']});

  // Only add the 4 validation fires to the map to avoid clutter
  if (fire.role === 'V') {
    Map.addLayer(falseColor, {}, fire.name + ' — False color', false);
    Map.addLayer(commonVis, {}, fire.name + ' — Common (orange)', false);
    Map.addLayer(onlyMedVis, {}, fire.name + ' — Mediterranean only (blue)', false);
    Map.addLayer(onlyIbVis, {}, fire.name + ' — Iberian only (red)', false);
  }
});

print('');
print('═══════════════════════════════════════════════════════');
print('   VISUALIZATION LEGEND (validation fires)');
print('   Orange: common detections');
print('   Blue:   AFD-S2 Mediterranean only');
print('   Red:    AFD-S2 Iberian only');
print('═══════════════════════════════════════════════════════');

// Center on the first validation fire
var firstVal = ee.Image(allFires[3].path);
Map.centerObject(firstVal.geometry(), 11);

// ============================================
// EXPORT RESULTS AS CSV TO GOOGLE DRIVE
// ============================================

var results = allFires.map(function(fire) {
  var img = ee.Image(fire.path);
  var geometry = img.geometry();
  
  var b3 = img.select('b3');
  var b5 = img.select('b5');
  var b6 = img.select('b6');
  
  // AFD-S2 Mediterranean
  var mask_med = b3.lt(b6.multiply(coef_med.a).add(coef_med.b))
    .and(b6.gte(coef_med.d))
    .and(b5.gte(coef_med.c).or(b6.gte(coef_med.d_extreme)));
  
  // AFD-S2 Iberian
  var mask_ib = b3.lt(b6.multiply(coef_ib.a).add(coef_ib.b))
    .and(b6.gte(coef_ib.d))
    .and(b5.gte(coef_ib.c).or(b6.gte(coef_ib.d_extreme)));
  
  var intersection = mask_med.and(mask_ib);
  var union = mask_med.or(mask_ib);
  var onlyMed = mask_med.and(mask_ib.not());
  var onlyIb = mask_ib.and(mask_med.not());
  
  var pix_med = mask_med.selfMask().reduceRegion({
    reducer: ee.Reducer.count(), geometry: geometry,
    scale: SCALE, maxPixels: 1e9, bestEffort: true
  }).values().get(0);
  
  var pix_ib = mask_ib.selfMask().reduceRegion({
    reducer: ee.Reducer.count(), geometry: geometry,
    scale: SCALE, maxPixels: 1e9, bestEffort: true
  }).values().get(0);
  
  var pix_inter = intersection.selfMask().reduceRegion({
    reducer: ee.Reducer.count(), geometry: geometry,
    scale: SCALE, maxPixels: 1e9, bestEffort: true
  }).values().get(0);
  
  var pix_union = union.selfMask().reduceRegion({
    reducer: ee.Reducer.count(), geometry: geometry,
    scale: SCALE, maxPixels: 1e9, bestEffort: true
  }).values().get(0);
  
  var pix_only_med = onlyMed.selfMask().reduceRegion({
    reducer: ee.Reducer.count(), geometry: geometry,
    scale: SCALE, maxPixels: 1e9, bestEffort: true
  }).values().get(0);
  
  var pix_only_ib = onlyIb.selfMask().reduceRegion({
    reducer: ee.Reducer.count(), geometry: geometry,
    scale: SCALE, maxPixels: 1e9, bestEffort: true
  }).values().get(0);
  
  var jaccard = ee.Number(pix_inter).divide(ee.Number(pix_union));
  
  return ee.Feature(null, {
    'name':           fire.name,
    'role':           fire.role,
    'pix_med':        pix_med,
    'pix_ib':         pix_ib,
    'pix_inter':      pix_inter,
    'pix_union':      pix_union,
    'pix_only_med':   pix_only_med,
    'pix_only_ib':    pix_only_ib,
    'jaccard':        jaccard,
    // WARNING: 0.09 ha/pixel overestimates the area by ~25-38% (see header)
    'ha_med':         ee.Number(pix_med).multiply(0.09),
    'ha_ib':          ee.Number(pix_ib).multiply(0.09)
  });
});

var resultsFC = ee.FeatureCollection(results);

Export.table.toDrive({
  collection: resultsFC,
  description: 'jaccard_per_fire',
  fileNamePrefix: 'jaccard_per_fire',
  fileFormat: 'CSV',
  selectors: ['name', 'role', 'pix_med', 'pix_ib', 'pix_inter', 
              'pix_union', 'pix_only_med', 'pix_only_ib', 
              'jaccard', 'ha_med', 'ha_ib']
});

print('');
print('▶ CSV export ready. Go to Tasks and run "jaccard_per_fire"');