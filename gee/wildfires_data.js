// ================================================================
// FeatureCollection of Iberian Peninsula wildfires (2020–2025)
// Source: EFFIS / user data
// ================================================================
// List of fires with basic metadata
var fires = [
  {
    name: 'Almonaster_2020',
    centerLat: 37.75,
    centerLon: -6.75,
    bufferKm: 15,
    startDate: '2020-08-24',
    endDate: '2020-09-05',
    cloudThreshold: 50
  },
  {
    name: 'Navalacruz_2021',
    centerLat: 40.42,
    centerLon: -4.87,
    bufferKm: 15,
    startDate: '2021-08-14',
    endDate: '2021-08-20',
    cloudThreshold: 50
  },
  {
    name: 'Ateca_2022',
    centerLat: 41.32,
    centerLon: -1.79,
    bufferKm: 15,
    startDate: '2022-07-19',
    endDate: '2022-07-20',
    cloudThreshold: 50
  },
  {
    name: 'Vall_dEbo_2022',
    centerLat: 38.79,
    centerLon: -0.17,
    bufferKm: 15,
    startDate: '2022-08-13',
    endDate: '2022-08-19',
    cloudThreshold: 50
  },
  {
    name: 'Albergaria_2024',
    centerLat: 40.68,
    centerLon: -8.47,
    bufferKm: 15,
    startDate: '2024-09-15',
    endDate: '2024-09-19',
    cloudThreshold: 50
  },
  {
    name: 'Una_de_Quintana_2025',
    centerLat: 42.08,
    centerLon: -6.14,
    bufferKm: 15,
    startDate: '2025-08-10',
    endDate: '2025-08-14',
    cloudThreshold: 50
  },
  {
    name: 'Buron_2025',
    centerLat: 43.02,
    centerLon: -5.04,
    bufferKm: 15,
    startDate: '2025-08-14',
    endDate: '2025-08-25',
    cloudThreshold: 50
  },
  {
    name: 'Losacio_2022',
    centerLat: 41.89,
    centerLon: -6.14,
    bufferKm: 15,
    startDate: '2022-07-10',
    endDate: '2022-07-25',
    cloudThreshold: 70
  },
  {
    name: 'Pinofranqueado_2023',
    centerLat: 40.30,
    centerLon: -6.33,
    bufferKm: 15,
    startDate: '2023-05-17',
    endDate: '2023-05-24',
    cloudThreshold: 50
  },
  {
    name: 'Sao_Tetonio_2023',
    centerLat: 37.51,
    centerLon: -8.69,
    bufferKm: 15,
    startDate: '2023-08-05',
    endDate: '2023-08-10',
    cloudThreshold: 50
  },
  {
    name: 'Lecrin_2022',
    centerLat: 36.88,
    centerLon: -3.58,
    bufferKm: 15,
    startDate: '2022-09-10',
    endDate: '2022-09-11',
    cloudThreshold: 50
  },
  {
    name: 'Sierra_Bermeja_2021',
    centerLat: 36.52,
    centerLon: -5.17,
    bufferKm: 15,
    startDate: '2021-09-08',
    endDate: '2021-09-12',
    cloudThreshold: 50
  },
  {
    name: 'Bejis_2022',
    centerLat: 39.89,
    centerLon: -0.70,
    bufferKm: 15,
    startDate: '2022-08-15',
    endDate: '2022-08-22',
    cloudThreshold: 50
  },
  {
    name: 'Cardoso_2025',
    centerLat: 41.17,
    centerLon: -3.43,
    bufferKm: 15,
    startDate: '2025-09-21',
    endDate: '2025-09-28',
    cloudThreshold: 70
  },
  {
    name: 'Santa_Coloma_2023',
    centerLat: 43.29,
    centerLon: -6.72,
    bufferKm: 15,
    startDate: '2023-03-29',
    endDate: '2023-03-31',
    cloudThreshold: 70
  },
  {
    name: 'Terrenho_2025',
    centerLat: 40.90,
    centerLon: -7.38,
    bufferKm: 15,
    startDate: '2025-08-10',
    endDate: '2025-08-17',
    cloudThreshold: 50
  },
  {
    name: 'Gargantilla_2025',
    centerLat: 40.20,
    centerLon: -5.90,
    bufferKm: 15,
    startDate: '2025-08-13',
    endDate: '2025-08-21',
    cloudThreshold: 70
  },
  {
    name: 'Ribeira_da_Gafa_2021',
    centerLat: 37.24,
    centerLon: -7.58,
    bufferKm: 15,
    startDate: '2021-08-16',
    endDate: '2021-08-18',
    cloudThreshold: 70
  },
  {
    name: 'Medeiros_2025',
    centerLat: 41.95,
    centerLon: -7.55,
    bufferKm: 15,
    startDate: '2025-08-13',
    endDate: '2025-08-20',
    cloudThreshold: 70
  },
  {
    name: 'Balteiro_2022',
    centerLat: 42.65,
    centerLon: -8.95,
    bufferKm: 15,
    startDate: '2022-08-04',
    endDate: '2022-08-06',
    cloudThreshold: 70
  }
];

// Convert the list into a FeatureCollection with SQUARE geometries
var fireFeatures = fires.map(function(fire) {
  // Create a circular buffer and then take its bounding box (square)
  var circleBuffer = ee.Geometry.Point([fire.centerLon, fire.centerLat])
    .buffer(fire.bufferKm * 1000);
  var squareGeom = circleBuffer.bounds();
  
  return ee.Feature(squareGeom, fire);
});

var fireCollection = ee.FeatureCollection(fireFeatures);

// Show on the map
Map.centerObject(fireCollection, 6);
Map.addLayer(fireCollection, {color: 'orange'}, 'Fires 2020–2025');

// Print for inspection
print('Fire FeatureCollection (square AOIs):', fireCollection);
print('Total number of fires:', fireCollection.size());

// (Optional) Export to your Drive or Assets
// Export.table.toDrive({
//   collection: fireCollection,
//   description: 'Fires_2020_2025_Peninsula',
//   fileFormat: 'GeoJSON'
// });