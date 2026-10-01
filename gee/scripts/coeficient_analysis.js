// ============================================
// VISUALIZATION: EVOLUTION OF THE AFD-S2 COEFFICIENTS
// Trend charts N=10 to N=20
// ============================================

// ----- SENSITIVITY DATA -----
var sensitivityData = ee.List([
  [10, 0.5764, 0.2275, -1045.86, 741.20, 4397.30, 1171.45, 3389.95, 969.21],
  [11, 0.5492, 0.2279, -979.93, 723.26, 4345.88, 1114.00, 3315.19, 937.93],
  [12, 0.5492, 0.2279, -979.93, 723.26, 4345.88, 1114.00, 3315.19, 937.93],
  [13, 0.5163, 0.2377, -942.23, 695.40, 4390.90, 1065.41, 3463.26, 994.53],
  [14, 0.5021, 0.2310, -907.42, 672.12, 4331.94, 1032.80, 3389.64, 976.40],
  [15, 0.5151, 0.2253, -897.43, 644.36, 4321.51, 989.44, 3370.97, 936.89],
  [16, 0.5018, 0.2214, -843.05, 647.10, 4229.91, 1002.18, 3273.69, 961.14],
  [17, 0.4772, 0.2310, -806.79, 637.12, 4249.92, 968.42, 3581.90, 1446.61],
  [18, 0.4772, 0.2310, -806.79, 637.12, 4249.92, 968.42, 3581.90, 1446.61],
  [19, 0.4840, 0.2246, -802.38, 615.74, 4228.96, 938.86, 3537.08, 1407.58],
  [20, 0.5009, 0.2271, -808.17, 596.61, 4238.57, 909.81, 3505.90, 1368.22]
]);

print('═════════════════════════════════════════════════');
print('   EVOLUTION OF THE AFD-S2 COEFFICIENTS (N=10→20)');
print('═════════════════════════════════════════════════');
print('');

// Prepare the chart data
var featureCollection = ee.FeatureCollection(
  sensitivityData.map(function(row) {
    var r = ee.List(row);
    return ee.Feature(null, {
      N: r.get(0),
      a_mean: r.get(1),
      a_std: r.get(2),
      b_mean: r.get(3),
      b_std: r.get(4),
      c_mean: r.get(5),
      c_std: r.get(6),
      d_mean: r.get(7),
      d_std: r.get(8)
    });
  })
);

// ============================================
// CHART 1: coefficient a
// ============================================

var chart_a = ui.Chart.feature.byFeature({
  features: featureCollection,
  xProperty: 'N',
  yProperties: ['a_mean']
}).setChartType('LineChart')
  .setOptions({
    title: 'Coefficient a (OLS slope) vs N',
    vAxis: {title: 'a (slope)', viewWindow: {min: 0.45, max: 0.60}},
    hAxis: {title: 'N (sample size)'},
    pointSize: 5,
    lineWidth: 2,
    colors: ['#1f77b4'],
    legend: {position: 'none'}
  });

print(chart_a);
print('Coefficient a: decreasing trend, stabilizing at ~0.50');
print('');

// ============================================
// CHART 2: coefficient b
// ============================================

var chart_b = ui.Chart.feature.byFeature({
  features: featureCollection,
  xProperty: 'N',
  yProperties: ['b_mean']
}).setChartType('LineChart')
  .setOptions({
    title: 'Coefficient b (-3σ) vs N',
    vAxis: {title: 'b (intercept -3σ)', viewWindow: {min: -1100, max: -750}},
    hAxis: {title: 'N (sample size)'},
    pointSize: 5,
    lineWidth: 2,
    colors: ['#ff7f0e'],
    legend: {position: 'none'}
  });

print(chart_b);
print('Coefficient b: less negative as N grows (more stable)');
print('');

// ============================================
// CHART 3: coefficient c
// ============================================

var chart_c = ui.Chart.feature.byFeature({
  features: featureCollection,
  xProperty: 'N',
  yProperties: ['c_mean']
}).setChartType('LineChart')
  .setOptions({
    title: 'Coefficient c (B11 p99) vs N',
    vAxis: {title: 'c (B11 99th percentile)', viewWindow: {min: 4100, max: 4500}},
    hAxis: {title: 'N (sample size)'},
    pointSize: 5,
    lineWidth: 2,
    colors: ['#2ca02c'],
    legend: {position: 'none'}
  });

print(chart_c);
print('Coefficient c: VERY STABLE - variation <4% ✓');
print('');

// ============================================
// CHART 4: coefficient d
// ============================================

var chart_d = ui.Chart.feature.byFeature({
  features: featureCollection,
  xProperty: 'N',
  yProperties: ['d_mean']
}).setChartType('LineChart')
  .setOptions({
    title: 'Coefficient d (B12 p99) vs N',
    vAxis: {title: 'd (B12 99th percentile)', viewWindow: {min: 3200, max: 3700}},
    hAxis: {title: 'N (sample size)'},
    pointSize: 5,
    lineWidth: 2,
    colors: ['#d62728'],
    legend: {position: 'none'}
  });

print(chart_d);
print('Coefficient d: stable (~9% variation)');
print('');

// ============================================
// CHART 5: all mean coefficients
// ============================================

var chart_all = ui.Chart.feature.byFeature({
  features: featureCollection,
  xProperty: 'N',
  yProperties: ['a_mean', 'c_mean', 'd_mean']
}).setChartType('LineChart')
  .setOptions({
    title: 'Evolution of the coefficients vs N (scaled)',
    vAxis: {title: 'Coefficient value'},
    hAxis: {title: 'N (sample size)'},
    pointSize: 4,
    lineWidth: 2,
    colors: ['#1f77b4', '#2ca02c', '#d62728'],
    series: {
      0: {labelInLegend: 'a (×1000)', targetAxisIndex: 0},
      1: {labelInLegend: 'c', targetAxisIndex: 0},
      2: {labelInLegend: 'd', targetAxisIndex: 0}
    }
  });

print(chart_all);
print('Comparison: c and d vary little, a fluctuates more');
print('');

// ============================================
// CHART 6: standard deviations
// ============================================

var chart_std = ui.Chart.feature.byFeature({
  features: featureCollection,
  xProperty: 'N',
  yProperties: ['a_std', 'b_std']
}).setChartType('LineChart')
  .setOptions({
    title: 'Evolution of the standard deviations vs N',
    vAxis: {title: 'Standard deviation'},
    hAxis: {title: 'N (sample size)'},
    pointSize: 4,
    lineWidth: 2,
    colors: ['#1f77b4', '#ff7f0e'],
    series: {
      0: {labelInLegend: 'std(a) [×1000]', targetAxisIndex: 0},
      1: {labelInLegend: 'std(b)', targetAxisIndex: 0}
    }
  });

print(chart_std);
print('Deviations: std(b) drops ~20%, std(a) stays stable');
print('');

// ============================================
// CHART 7: coefficient of variation
// ============================================

// Compute the CV
var fcWithCV = featureCollection.map(function(f) {
  var a_mean = ee.Number(f.get('a_mean'));
  var a_std = ee.Number(f.get('a_std'));
  var b_mean = ee.Number(f.get('b_mean'));
  var b_std = ee.Number(f.get('b_std'));
  var c_mean = ee.Number(f.get('c_mean'));
  var c_std = ee.Number(f.get('c_std'));
  var d_mean = ee.Number(f.get('d_mean'));
  var d_std = ee.Number(f.get('d_std'));
  
  return f.set({
    CV_a: a_std.divide(a_mean).multiply(100),
    CV_b: b_std.divide(b_mean.abs()).multiply(100),
    CV_c: c_std.divide(c_mean).multiply(100),
    CV_d: d_std.divide(d_mean).multiply(100)
  });
});

var chart_cv = ui.Chart.feature.byFeature({
  features: fcWithCV,
  xProperty: 'N',
  yProperties: ['CV_a', 'CV_b', 'CV_c', 'CV_d']
}).setChartType('LineChart')
  .setOptions({
    title: 'Coefficient of variation (CV = std/mean × 100%) vs N',
    vAxis: {title: 'CV (%)', viewWindow: {min: 0, max: 80}},
    hAxis: {title: 'N (sample size)'},
    pointSize: 4,
    lineWidth: 2,
    colors: ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'],
    series: {
      0: {labelInLegend: 'CV(a)'},
      1: {labelInLegend: 'CV(b)'},
      2: {labelInLegend: 'CV(c)'},
      3: {labelInLegend: 'CV(d)'}
    }
  });

print(chart_cv);

print('');
print('═════════════════════════════════════════════════');
print('   CONCLUSIONS');
print('═════════════════════════════════════════════════');
print('');
print('1. STABILITY PER COEFFICIENT:');
print('   ✓ c (B11 p99): VERY STABLE - CV ~21%');
print('   ✓ d (B12 p99): MODERATE - CV ~39%');
print('   ⚠ a (slope): HIGH VARIABILITY - CV ~45%');
print('   ⚠ b (intercept): VERY HIGH VARIABILITY - CV ~74%');
print('');
print('2. EFFECT OF INCREASING N (10→20):');
print('   - std(b) drops ~20% (better stability)');
print('   - std(a) practically unchanged (~0%)');
print('   - c and d stabilize for N>15');
print('');
print('3. METHODOLOGICAL RECOMMENDATION:');
print('   ✓ c and d can be used as FIXED THRESHOLDS');
print('   ⚠ a and b must be RECALIBRATED per region/biome');
print('   ✓ N=20 gives robust estimates');
print('   ✓ A fixed validation set is essential for comparability');
print('');
print('4. RECOMMENDED FINAL COEFFICIENTS (N=20):');
print('   a = 0.501 ± 0.227  (CV = 45.3%)');
print('   b = -808 ± 597     (CV = 73.8%)');
print('   c = 4239 ± 910     (CV = 21.5%) ← MOST STABLE');
print('   d = 3506 ± 1368    (CV = 39.0%)');
print('');
print('5. PRACTICAL IMPLICATIONS:');
print('   - The high variability of a and b suggests');
print('     ecological/climatic differences between fires');
print('   - c (SWIR1 p99) is the MOST reliable coefficient');
print('   - Consider regional calibration where possible');
print('');
print('═════════════════════════════════════════════════');