// ============================================
// TOTAL PIXEL COUNT PER FIRE
// Counts valid pixels in the 30x30 km AOI
// for every HLS asset in the sample
// ============================================
//
// NOTES:
// - Pixel size: the assets are on an EPSG:4326 grid (~0.000269° pixels),
//   ~30 m north-south but only ~22-24 m east-west at Iberian latitudes, so a
//   pixel covers ~650-720 m², not 900 m². That is why px_total exceeds
//   px_theoretical by up to ~33% in scenes with little masking:
//   px_theoretical (area / 900 m²) is NOT the real number of pixels.
// - Area model: geometry.area() uses a spherical Earth. On the WGS84
//   ellipsoid area_ha_aoi is ~0.1-0.3% larger (difference grows with latitude).
// - Use python/pixels_per_fire.py for ellipsoidal areas and the true mean
//   pixel area per scene (px_area_m2).
// ============================================

var base = 'projects/stunning-hull-476912-p8/assets/';

var allFires = [
  {name: 'Almonaster la Real', path: base + 'Almonaster_20200829_HLSS30'},
  {name: 'Navalacruz',         path: base + 'Navalacruz_20210815_HLSL30'},
  {name: 'Ribeira da Gafa',    path: base + 'Ribeira_da_Gafa_20210817_HLSS30'},
  {name: 'Sierra Bermeja',     path: base + 'Sierra_Bermeja_20210909_HLSL30'},
  {name: 'Losacio',            path: base + 'Losacio_20220718_HLSS30'},
  {name: 'Ateca',              path: base + 'Ateca_20220719_HLSL30'},
  {name: 'Balteiro',           path: base + 'Balteiro_20220805_HLSS30'},
  {name: "Vall d'Ebo",         path: base + 'Vall_dEbo_20220814_HLSL30'},
  {name: 'Bejís',              path: base + 'Bejis_20220818_HLSS30'},
  {name: 'Lecrín',             path: base + 'Lecrin_2022_20220910_HLSS30'},
  {name: 'Santa Coloma',       path: base + 'Santa_Coloma_20230329_HLSL30'},
  {name: 'Pinofranqueado',     path: base + 'Pinofranqueado_20230519_HLSS30'},
  {name: 'São Tetónio',        path: base + 'Sao_Tetonio_20230807_HLSS30'},
  {name: 'Albergaria',         path: base + 'Albergaria_20240918_HLSS30'},
  // Previously pointed to Terrenho_2025_20250811_1121_HLSS30, an export in
  // EPSG:32629 (UTM 29N, 30 m) with a different AOI. Fixed to the EPSG:4326
  // asset used by coeficients.js and jaccard.js
  {name: 'Terrenho',           path: base + 'Terrenho_20250811_HLSS30'},
  {name: 'Una de Quintana',    path: base + 'Una_de_Quintana_20250811_HLSS30'},
  {name: 'Medeiros',           path: base + 'Medeiros_20250816_HLSS30'},
  {name: 'Burón',              path: base + 'Buron_20250817_HLSL30'},
  {name: 'Gargantilla',        path: base + 'Gargantilla_20250817_HLSL30'},
  {name: 'Cardoso',            path: base + 'Cardoso_20250926_HLSS30'},
];

// Function that counts valid pixels in band b3
function countPixels(fire) {
  var img = ee.Image(fire.path);
  var geometry = img.geometry();

  // Valid pixels in b3 (Red): value >= 0 and not nodata
  var valid = img.select('b3').gte(0);

  var count = valid.selfMask().reduceRegion({
    reducer: ee.Reducer.count(),
    geometry: geometry,
    scale: 30,
    maxPixels: 1e9,
    bestEffort: true
  });

  // Total AOI area in hectares (spherical Earth model, see header)
  var area_ha = geometry.area().divide(10000);

  return ee.Feature(null, {
    'fire':           fire.name,
    'px_total':       count.get('b3'),
    'area_ha_aoi':    area_ha,
    'px_theoretical': ee.Number(area_ha).multiply(10000).divide(900)
                       // 1 HLS px = 30x30 m = 900 m² (nominal: the real
                       // pixel area on this grid is ~650-720 m², see header)
  });
}

// Process all fires
var results = ee.FeatureCollection(
  allFires.map(function(fire) {
    return countPixels(fire);
  })
);

// Show in the console
print('=== TOTAL PIXELS PER FIRE ===');
print(results);

// Export to CSV
Export.table.toDrive({
  collection: results,
  description: 'pixels_per_fire',
  fileNamePrefix: 'pixels_per_fire',
  fileFormat: 'CSV',
  selectors: ['fire', 'px_total', 'area_ha_aoi', 'px_theoretical']
});

// Compute cumulative total
var totalPx = results.aggregate_sum('px_total');
print('Cumulative total pixels (20 fires):', totalPx);