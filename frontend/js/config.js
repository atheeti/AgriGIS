/* ============================================================
   TerraGIS Frontend  |  js/config.js
   ──────────────────────────────────────────────────────────
   Shared constants, INDICES display configuration, and
   colour-mapping helpers.

   NOTE: GEE formulas and evalscripts live in backend/indices.py.
         This file only contains what the frontend needs for:
           • building index buttons
           • drawing the legend
           • classifying the mean value into a text label
           • colouring the histogram bars
   ============================================================ */

// ── SHARED APPLICATION STATE ─────────────────────────────────
const AppState = {
  map:           null,   // Leaflet map instance
  drawnLayer:    null,   // Currently drawn polygon/circle/rectangle
  overlayLayer:  null,   // GEE tile layer currently shown on map
  trueColorLayer:  null, // Sentinel-2 true-colour composite tile layer (ground-truthing)
  falseColorLayer: null, // Sentinel-2 false-colour composite tile layer (ground-truthing)
  selectedIndex: null,   // e.g. 'NDVI'
  lastResult:    null,   // Last /api/calculate response + display cfg
  lastCrossSection: null, // Last /api/cross-section response (for PDF report)
  histChart:     null,   // Chart.js instance (histogram)
  xsChart:       null,   // Chart.js instance (cross-section line graph)
  overlayOpacity: 0.82,  // current classification layer opacity
  isLoading:     false,
  apiReady:      false,  // true when backend health check passes
};

// ── SPECTRAL INDEX DISPLAY CONFIGURATION ─────────────────────
const INDICES = {

  NDVI: {
    full:     'Normalized Difference Vegetation Index',
    formula:  '(NIR − Red) / (NIR + Red)',
    color:    '#4CAF50',
    disp:     [-0.2, 1.0],
    stops:    ['#d73027','#f46d43','#fdae61','#fee08b','#ffffbf','#d9ef8b','#a6d96a','#66bd63','#1a9850'],
    classify: v => v<0?'Water / Built-up':v<0.2?'Bare Soil':v<0.4?'Sparse Vegetation':v<0.6?'Moderate Growth':v<0.8?'Healthy Crop':'Dense Vegetation',
    classes: [
      {range:[-1,  0  ],label:'Water',              color:'#4575b4'},
      {range:[-1,  0  ],label:'Built-up / Non-Veg', color:'#707070'},
      {range:[0,   0.2],label:'Bare Soil',        color:'#d73027'},
      {range:[0.2, 0.4],label:'Sparse Vegetation',color:'#fdae61'},
      {range:[0.4, 0.6],label:'Moderate Growth',  color:'#fee08b'},
      {range:[0.6, 0.8],label:'Healthy Crop',     color:'#66bd63'},
      {range:[0.8, 1  ],label:'Dense Vegetation', color:'#1a9850'},
    ],
  },

  NDMI: {
    full:     'Normalized Difference Moisture Index',
    formula:  '(NIR − SWIR1) / (NIR + SWIR1)',
    color:    '#29B6F6',
    disp:     [-0.5, 0.6],
    stops:    ['#8c510a','#bf812d','#dfc27d','#f6e8c3','#f5f5f5','#c7eae5','#80cdc1','#35978f','#01665e'],
    classify: v => v<-0.3?'Very Dry':v<0?'Dry':v<0.2?'Normal Moisture':v<0.4?'Moist':'Very Moist',
    classes: [
      {range:[-1,  -0.3],label:'Very Dry',       color:'#8c510a'},
      {range:[-0.3, 0  ],label:'Dry',             color:'#dfc27d'},
      {range:[0,    0.2],label:'Normal Moisture', color:'#c7eae5'},
      {range:[0.2,  0.4],label:'Moist',           color:'#35978f'},
      {range:[0.4,  1  ],label:'Very Moist',      color:'#01665e'},
    ],
  },

  EVI: {
    full:     'Enhanced Vegetation Index',
    formula:  '2.5×(NIR−Red) / (NIR + 6·Red − 7.5·Blue + 1)',
    color:    '#8BC34A',
    disp:     [0, 0.8],
    stops:    ['#ffffe5','#f7fcb9','#d9f0a3','#addd8e','#78c679','#41ab5d','#238443','#006837','#004529'],
    classify: v => v<0.1?'No Vegetation':v<0.3?'Sparse':v<0.5?'Moderate':v<0.7?'Healthy':'Very Dense',
    classes: [
      {range:[0,   0.1],label:'No Vegetation',color:'#ffffe5'},
      {range:[0.1, 0.3],label:'Sparse',        color:'#d9f0a3'},
      {range:[0.3, 0.5],label:'Moderate',       color:'#78c679'},
      {range:[0.5, 0.7],label:'Healthy',         color:'#238443'},
      {range:[0.7, 1  ],label:'Very Dense',       color:'#004529'},
    ],
  },

  MDWI: {
    full:     'Modified Difference Water Index',
    formula:  '(Green − SWIR1) / (Green + SWIR1)',
    color:    '#039BE5',
    disp:     [-0.5, 0.5],
    stops:    ['#d01c1f','#f46d43','#fdae61','#ffffbf','#abd9e9','#74add1','#4575b4','#313695'],
    classify: v => v<-0.3?'Very Dry Land':v<0?'Dry':v<0.2?'Wet Soil':'Water Body',
    classes: [
      {range:[-1,  -0.3],label:'Very Dry Land',color:'#d01c1f'},
      {range:[-0.3, 0  ],label:'Dry',           color:'#fdae61'},
      {range:[0,    0.2],label:'Wet Soil',       color:'#abd9e9'},
      {range:[0.2,  1  ],label:'Water Body',     color:'#313695'},
    ],
  },

  SAVI: {
    full:     'Soil Adjusted Vegetation Index',
    formula:  '((NIR − Red) / (NIR + Red + 0.5)) × 1.5',
    color:    '#9CCC65',
    disp:     [-0.2, 1.0],
    stops:    ['#8b4513','#cd853f','#daa520','#ffd700','#9acd32','#32cd32','#228b22','#006400'],
    classify: v => v<0.1?'Bare Soil':v<0.3?'Very Sparse':v<0.5?'Sparse–Moderate':v<0.7?'Dense Vegetation':'Very Dense',
    classes: [
      {range:[-1,  0.1],label:'Bare Soil',       color:'#cd853f'},
      {range:[0.1, 0.3],label:'Very Sparse',      color:'#daa520'},
      {range:[0.3, 0.5],label:'Sparse–Moderate',  color:'#9acd32'},
      {range:[0.5, 0.7],label:'Dense Vegetation', color:'#228b22'},
      {range:[0.7, 1.5],label:'Very Dense',        color:'#006400'},
    ],
  },

  GNDVI: {
    full:     'Green Normalized Difference Vegetation Index',
    formula:  '(NIR − Green) / (NIR + Green)',
    color:    '#66BB6A',
    disp:     [0, 0.9],
    stops:    ['#ffffcc','#d9f0a3','#addd8e','#78c679','#41ab5d','#238443','#006837'],
    classify: v => v<0.2?'Low Chlorophyll':v<0.4?'Moderate':v<0.6?'Good':'High Chlorophyll',
    classes: [
      {range:[0,   0.2],label:'Low Chlorophyll', color:'#ffffcc'},
      {range:[0.2, 0.4],label:'Moderate',         color:'#addd8e'},
      {range:[0.4, 0.6],label:'Good',             color:'#78c679'},
      {range:[0.6, 1  ],label:'High Chlorophyll', color:'#006837'},
    ],
  },

  GCI: {
    full:     'Green Chlorophyll Index',
    formula:  '(NIR / Green) − 1',
    color:    '#AED581',
    disp:     [0, 10],
    stops:    ['#ffffe5','#f7fcb9','#d9f0a3','#addd8e','#78c679','#41ab5d','#238443','#006837'],
    classify: v => v<1?'Very Low':v<3?'Low':v<5?'Moderate':v<7?'High':'Very High',
    classes: [
      {range:[0, 1 ],label:'Very Low', color:'#ffffe5'},
      {range:[1, 3 ],label:'Low',       color:'#d9f0a3'},
      {range:[3, 5 ],label:'Moderate',  color:'#78c679'},
      {range:[5, 7 ],label:'High',       color:'#238443'},
      {range:[7, 15],label:'Very High',  color:'#006837'},
    ],
  },

  SIPI: {
    full:     'Structure Insensitive Pigment Index',
    formula:  '(NIR − Blue) / (NIR − Red)',
    color:    '#FF8F00',
    disp:     [0.8, 1.8],
    stops:    ['#9e0142','#d53e4f','#f46d43','#fdae61','#ffffbf','#e6f598','#abdda4','#66c2a5','#3288bd'],
    classify: v => v<1.0?'Stressed':v<1.3?'Mild Stress':v<1.6?'Normal':'Healthy',
    classes: [
      {range:[0,   1.0],label:'Stressed',           color:'#d53e4f'},
      {range:[1.0, 1.3],label:'Mild Stress',         color:'#f46d43'},
      {range:[1.3, 1.6],label:'Normal',              color:'#e6f598'},
      {range:[1.6, 2.5],label:'Healthy (Low Carot.)',color:'#3288bd'},
    ],
  },

  NBR: {
    full:     'Normalized Burn Ratio',
    formula:  '(NIR − SWIR2) / (NIR + SWIR2)',
    color:    '#FF5722',
    disp:     [-0.5, 1.0],
    stops:    ['#7b2d00','#c0392b','#e67e22','#f1c40f','#2ecc71','#27ae60','#1a5276'],
    classify: v => v<-0.1?'High Burn Severity':v<0.1?'Moderate Burn':v<0.3?'Low Severity':v<0.6?'Unburned':'Healthy/Dense',
    classes: [
      {range:[-1,  -0.1],label:'High Burn Severity',color:'#c0392b'},
      {range:[-0.1, 0.1],label:'Moderate Burn',      color:'#e67e22'},
      {range:[0.1,  0.3],label:'Low Severity',        color:'#f1c40f'},
      {range:[0.3,  0.6],label:'Unburned',            color:'#2ecc71'},
      {range:[0.6,  1  ],label:'Healthy / Dense',     color:'#1a5276'},
    ],
  },

  MGRVI: {
    full:     'Modified Green Red Vegetation Index',
    formula:  '(Green² − Red²) / (Green² + Red²)',
    color:    '#69F0AE',
    disp:     [-0.3, 0.8],
    stops:    ['#a50026','#d73027','#fdae61','#ffffbf','#a6d96a','#1a9850'],
    classify: v => v<0?'Stressed':v<0.2?'Low Biomass':v<0.4?'Moderate':'High Biomass',
    classes: [
      {range:[-1,  0  ],label:'Stressed',    color:'#d73027'},
      {range:[0,   0.2],label:'Low Biomass', color:'#fdae61'},
      {range:[0.2, 0.4],label:'Moderate',     color:'#a6d96a'},
      {range:[0.4, 1  ],label:'High Biomass', color:'#1a9850'},
    ],
  },

  NDWI: {
    full:     'Normalized Difference Water Index',
    formula:  '(Green − NIR) / (Green + NIR)',
    color:    '#00BCD4',
    disp:     [-0.5, 0.5],
    stops:    ['#d7191c','#fdae61','#ffffbf','#abd9e9','#2c7bb6','#054e9e'],
    classify: v => v<-0.3?'Dry Land':v<0?'Soil':v<0.2?'Moist Soil':v<0.5?'Water Body':'Open Water',
    classes: [
      {range:[-1,  -0.3],label:'Dry Land',  color:'#d7191c'},
      {range:[-0.3, 0  ],label:'Soil',        color:'#fdae61'},
      {range:[0,    0.2],label:'Moist Soil',  color:'#abd9e9'},
      {range:[0.2,  0.5],label:'Water Body',  color:'#2c7bb6'},
      {range:[0.5,  1  ],label:'Open Water',  color:'#054e9e'},
    ],
  },

  LSWI: {
    full:     'Land Surface Water Index',
    formula:  '(NIR − SWIR1) / (NIR + SWIR1)',
    color:    '#26A69A',
    disp:     [-0.5, 0.6],
    stops:    ['#a52a2a','#deb887','#f6e8c3','#c7eae5','#80cdc1','#35978f','#01665e'],
    classify: v => v<-0.2?'Very Dry / Bare':v<0?'Dry Vegetation':v<0.2?'Normal Moisture':v<0.4?'High Moisture':'Flooded / Open Water',
    classes: [
      {range:[-1,  -0.2],label:'Very Dry / Bare',       color:'#a52a2a'},
      {range:[-0.2, 0   ],label:'Dry Vegetation',        color:'#deb887'},
      {range:[0,    0.2],label:'Normal Moisture',        color:'#c7eae5'},
      {range:[0.2,  0.4],label:'High Moisture',          color:'#35978f'},
      {range:[0.4,  1  ],label:'Flooded / Open Water',   color:'#01665e'},
    ],
  },

};

// ── COLOUR HELPERS ────────────────────────────────────────────
function hexToRgb(hex) {
  return [
    parseInt(hex.slice(1,3), 16),
    parseInt(hex.slice(3,5), 16),
    parseInt(hex.slice(5,7), 16),
  ];
}

function valueToRGB(value, stops, min, max) {
  const t  = Math.max(0, Math.min(1, (value - min) / (max - min)));
  const n  = stops.length - 1;
  const i  = Math.min(Math.floor(t * n), n - 1);
  const f  = t * n - i;
  const c1 = hexToRgb(stops[i]);
  const c2 = hexToRgb(stops[i + 1]);
  return [
    Math.round(c1[0] + (c2[0] - c1[0]) * f),
    Math.round(c1[1] + (c2[1] - c1[1]) * f),
    Math.round(c1[2] + (c2[2] - c1[2]) * f),
  ];
}

console.log('[TerraGIS] config.js loaded —', Object.keys(INDICES).length, 'indices.');
