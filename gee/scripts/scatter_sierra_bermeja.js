// ============================================
// REAL SCATTER PLOT: Sierra Bermeja
// Exports a CSV with ρ_Red vs ρ_SWIR2 for Fig. 3.2
// ============================================

var asset = 'projects/stunning-hull-476912-p8/assets/' +
            'Sierra_Bermeja_20210909_HLSL30';

// AFD-S2 Mediterranean coefficients
var coef_med = {a: 0.743, b: -680, c: 4750, d: 3550};
// AFD-S2 Iberian coefficients
var coef_ib  = {a: 0.5009, b: -808.17, c: 4238.57, d: 3505.90};

var img = ee.Image(asset);
var geometry = img.geometry();

var red   = img.select('b3');
var swir1 = img.select('b5');
var swir2 = img.select('b6');

// Med and Ib fire masks
var fire_med = red.lt(swir2.multiply(coef_med.a).add(coef_med.b))
  .and(swir2.gte(coef_med.d))
  .and(swir1.gte(coef_med.c).or(swir2.gte(10000)));

var fire_ib = red.lt(swir2.multiply(coef_ib.a).add(coef_ib.b))
  .and(swir2.gte(coef_ib.d))
  .and(swir1.gte(coef_ib.c).or(swir2.gte(10000)));

// Pixel category: 0=no fire, 1=Med only, 2=Ib only, 3=both
var category = fire_med.multiply(1)
  .add(fire_ib.multiply(2))
  .rename('category');

// Sample pixels (random sample to keep the CSV small)
var sample = img.select(['b3','b6'])
  .addBands(category)
  .sample({
    region: geometry,
    scale: 30,
    //numPixels: 5000,
    seed: 42,
    geometries: false
  });

Export.table.toDrive({
  collection: sample,
  description: 'scatter_Red_SWIR2_Sierra_Bermeja',
  fileNamePrefix: 'scatter_Red_SWIR2_Sierra_Bermeja',
  fileFormat: 'CSV',
  selectors: ['b3', 'b6', 'category']
});

print('▶ Run the task in Tasks to export the CSV');
print('Columns: b3=Red, b6=SWIR2, category (0=bg, 1=MedOnly, 2=IbOnly, 3=both)');