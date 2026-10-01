// ============================================
// AFD-S2 COEFFICIENT SENSITIVITY ANALYSIS
// N=10 to N=20 with fixed validation set
// ============================================

var allAssets = [
  'projects/stunning-hull-476912-p8/assets/Albergaria_20240918_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Almonaster_20200829_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Ateca_20220719_HLSL30',
  'projects/stunning-hull-476912-p8/assets/Balteiro_20220805_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Bejis_20220818_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Buron_20250817_HLSL30',
  'projects/stunning-hull-476912-p8/assets/Cardoso_20250926_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Gargantilla_20250817_HLSL30',
  'projects/stunning-hull-476912-p8/assets/Lecrin_2022_20220910_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Losacio_20220718_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Medeiros_20250816_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Navalacruz_20210815_HLSL30',
  'projects/stunning-hull-476912-p8/assets/Pinofranqueado_20230519_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Ribeira_da_Gafa_20210817_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Santa_Coloma_20230329_HLSL30',
  'projects/stunning-hull-476912-p8/assets/Sao_Tetonio_20230807_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Sierra_Bermeja_20210909_HLSL30',
  'projects/stunning-hull-476912-p8/assets/Terrenho_20250811_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Una_de_Quintana_20250811_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Vall_dEbo_20220814_HLSL30'
];

// ----- FIXED VALIDATION -----
// N=10-11: 2 fires
var validation2 = [
  'projects/stunning-hull-476912-p8/assets/Sierra_Bermeja_20210909_HLSL30',
  'projects/stunning-hull-476912-p8/assets/Losacio_20220718_HLSS30'
];

// N=12-17: 3 fires
var validation3 = [
  'projects/stunning-hull-476912-p8/assets/Sierra_Bermeja_20210909_HLSL30',
  'projects/stunning-hull-476912-p8/assets/Losacio_20220718_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Vall_dEbo_20220814_HLSL30'
];

// N=18-20: 4 fires
var validation4 = [
  'projects/stunning-hull-476912-p8/assets/Sierra_Bermeja_20210909_HLSL30',
  'projects/stunning-hull-476912-p8/assets/Losacio_20220718_HLSS30',
  'projects/stunning-hull-476912-p8/assets/Vall_dEbo_20220814_HLSL30',
  'projects/stunning-hull-476912-p8/assets/Gargantilla_20250817_HLSL30'
];

// Calibration pool (excludes the 4 validation fires)
var calibPool = allAssets.filter(function(asset) {
  return validation4.indexOf(asset) === -1;  // 16 assets available
});

// ----- SPLIT TABLE -----
var splitTable = [
  {total: 10, calib: 8,  validSet: validation2},
  {total: 11, calib: 9,  validSet: validation2},
  {total: 12, calib: 9,  validSet: validation3},
  {total: 13, calib: 10, validSet: validation3},
  {total: 14, calib: 11, validSet: validation3},
  {total: 15, calib: 12, validSet: validation3},
  {total: 16, calib: 13, validSet: validation3},
  {total: 17, calib: 14, validSet: validation3},
  {total: 18, calib: 14, validSet: validation4},
  {total: 19, calib: 15, validSet: validation4},
  {total: 20, calib: 16, validSet: validation4}
];

var SCALE = 30;

// ============================================
// FUNCTION: compute coefficients for ONE asset
// ============================================
function computeCoefficients(assetPath) {
  var img = ee.Image(assetPath);
  var geometry = img.geometry();

  var b3 = img.select('b3');  // Red   (B4)
  var b5 = img.select('b5');  // SWIR1 (B11)
  var b6 = img.select('b6');  // SWIR2 (B12)

  // OLS regression: X = b6 (SWIR2), Y = b3 (Red)
  var regression = b6.addBands(b3).reduceRegion({
    reducer: ee.Reducer.linearFit(),
    geometry: geometry,
    scale: SCALE,
    maxPixels: 1e9,
    bestEffort: true
  });

  var a = ee.Number(regression.get('scale'));
  var b = ee.Number(regression.get('offset'));

  // σ of the residuals
  var predicted = b6.multiply(a).add(b);
  var residuals  = b3.subtract(predicted);

  var sigma = ee.Number(
    residuals.reduceRegion({
      reducer: ee.Reducer.stdDev(),
      geometry: geometry,
      scale: SCALE,
      maxPixels: 1e9,
      bestEffort: true
    }).get('b3')
  );

  // b adjusted by -3σ (lower prediction bound)
  var b_adjusted = b.subtract(sigma.multiply(3));

  // 99th percentiles for c (B11) and d (B12)
  var percentiles = img.select(['b5', 'b6']).reduceRegion({
    reducer: ee.Reducer.percentile([99]),
    geometry: geometry,
    scale: SCALE,
    maxPixels: 1e9,
    bestEffort: true
  });

  return ee.Dictionary({
    asset: assetPath,
    a:     a,
    b:     b_adjusted,
    sigma: sigma,
    c:     ee.Number(percentiles.get('b5')),
    d:     ee.Number(percentiles.get('b6'))
  });
}

// ============================================
// FUNCTION: mean and std over a set of assets
// ============================================
function computeMeanCoefficients(assetSubset) {
  var coeffList = assetSubset.map(computeCoefficients);

  var aArr = ee.Array(coeffList.map(function(d) { return ee.Dictionary(d).getNumber('a'); }));
  var bArr = ee.Array(coeffList.map(function(d) { return ee.Dictionary(d).getNumber('b'); }));
  var cArr = ee.Array(coeffList.map(function(d) { return ee.Dictionary(d).getNumber('c'); }));
  var dArr = ee.Array(coeffList.map(function(d) { return ee.Dictionary(d).getNumber('d'); }));

  return {
    a_mean: aArr.reduce(ee.Reducer.mean(),   [0]).get([0]),
    a_std:  aArr.reduce(ee.Reducer.stdDev(), [0]).get([0]),
    b_mean: bArr.reduce(ee.Reducer.mean(),   [0]).get([0]),
    b_std:  bArr.reduce(ee.Reducer.stdDev(), [0]).get([0]),
    c_mean: cArr.reduce(ee.Reducer.mean(),   [0]).get([0]),
    c_std:  cArr.reduce(ee.Reducer.stdDev(), [0]).get([0]),
    d_mean: dArr.reduce(ee.Reducer.mean(),   [0]).get([0]),
    d_std:  dArr.reduce(ee.Reducer.stdDev(), [0]).get([0])
  };
}

// ============================================
// MAIN ANALYSIS
// ============================================

print('═════════════════════════════════════════════════');
print('   AFD-S2 SENSITIVITY ANALYSIS (N=10 to N=20)');
print('   Incremental fixed validation');
print('   Calibration pool: ' + calibPool.length + ' fires');
print('═════════════════════════════════════════════════');
print('');
print('FIXED VALIDATION:');
print('  N=10-11: Sierra_Bermeja + Losacio');
print('  N=12-17: + Vall_dEbo');
print('  N=18-20: + Gargantilla');
print('');

splitTable.forEach(function(split) {

  var calibAssets = calibPool.slice(0, split.calib);
  var validAssets = split.validSet;

  print('══════════════════════════════════════════════');
  print('TOTAL=' + split.total +
        '  |  CALIBRATION=' + split.calib +
        '  |  VALIDATION=' + validAssets.length);
  print('══════════════════════════════════════════════');

  var mc = computeMeanCoefficients(calibAssets);

  print('  Mean coefficients (± std. dev.):');
  print('    a:', mc.a_mean, '±', mc.a_std);
  print('    b:', mc.b_mean, '±', mc.b_std);
  print('    c:', mc.c_mean, '±', mc.c_std);
  print('    d:', mc.d_mean, '±', mc.d_std);
  print('');

  print('  CALIBRATION fires:');
  calibAssets.forEach(function(a) {
    print('    [C]', a.split('/').slice(-1)[0]);
  });
  print('  VALIDATION fires (fixed):');
  validAssets.forEach(function(a) {
    print('    [V]', a.split('/').slice(-1)[0]);
  });
  print('');
});

// ============================================
// INDIVIDUAL COEFFICIENTS PER FIRE
// ============================================
print('═════════════════════════════════════════════════');
print('   INDIVIDUAL COEFFICIENTS (20 FIRES)');
print('═════════════════════════════════════════════════');
print('');

allAssets.forEach(function(assetPath) {
  var name   = assetPath.split('/').slice(-1)[0];
  var coeffs = computeCoefficients(assetPath);
  var role   = validation4.indexOf(assetPath) !== -1 ? '[VALIDATION]' : '[calibration]';

  print('──────────────────────────────────');
  print(role, name);
  print('  a:      ', coeffs.get('a'));
  print('  b(-3σ): ', coeffs.get('b'));
  print('  σ:      ', coeffs.get('sigma'));
  print('  c(p99): ', coeffs.get('c'));
  print('  d(p99): ', coeffs.get('d'));
  print('');
});

print('═════════════════════════════════════════════════');
print('   END OF ANALYSIS');
print('═════════════════════════════════════════════════');
print('');
print('Fixed validation fires:');
print('  1. Sierra_Bermeja_20210909_HLSL30 (HLSL30, 2021)');
print('  2. Losacio_20220718_HLSS30 (HLSS30, outlier)');
print('  3. Vall_dEbo_20220814_HLSL30 (HLSL30, 2022)');
print('  4. Gargantilla_20250817_HLSL30 (HLSL30, 2025)');

// Min/max of the individual coefficients over the calibration pool
var a_vals = [];
var b_vals = [];
var c_vals = [];
var d_vals = [];

calibPool.forEach(function(asset) {
  var c = computeCoefficients(asset);
  a_vals.push(c.getNumber('a').getInfo());
  b_vals.push(c.getNumber('b').getInfo());
  c_vals.push(c.getNumber('c').getInfo());
  d_vals.push(c.getNumber('d').getInfo());
});

print('Min/Max:');
print('  a:', Math.min.apply(null, a_vals), '/', Math.max.apply(null, a_vals));
print('  b:', Math.min.apply(null, b_vals), '/', Math.max.apply(null, b_vals));
print('  c:', Math.min.apply(null, c_vals), '/', Math.max.apply(null, c_vals));
print('  d:', Math.min.apply(null, d_vals), '/', Math.max.apply(null, d_vals));