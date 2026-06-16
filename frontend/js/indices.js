/* =============================================
   AgriGIS – Index Metadata & Legend Rendering
   ============================================= */

const INDEX_CONFIG = {
  NDVI: {
    label: "NDVI",
    fullName: "Normalized Difference Vegetation Index",
    description: "Measures vegetation density and health. Higher values indicate denser, healthier vegetation.",
    formula: "(NIR − RED) / (NIR + RED)",
    min: -1, max: 1,
    goodRange: [0.4, 0.8],
    unit: "",
    gradient: "linear-gradient(to right, #8B0000, #FF4500, #FFFF00, #ADFF2F, #32CD32, #006400)",
    ticks: ["-1.0", "-0.5", "0.0", "0.5", "1.0"],
  },
  NDMI: {
    label: "NDMI",
    fullName: "Normalized Difference Moisture Index",
    description: "Detects vegetation water content. Positive values indicate well-watered vegetation.",
    formula: "(NIR − SWIR1) / (NIR + SWIR1)",
    min: -1, max: 1,
    goodRange: [0.0, 0.6],
    unit: "",
    gradient: "linear-gradient(to right, #8B4513, #DEB887, #FFFACD, #87CEEB, #1E90FF, #00008B)",
    ticks: ["-1.0", "-0.5", "0.0", "0.5", "1.0"],
  },
  EVI: {
    label: "EVI",
    fullName: "Enhanced Vegetation Index",
    description: "Improved vegetation index with canopy background and atmospheric corrections.",
    formula: "2.5 × (NIR − RED) / (NIR + 6×RED − 7.5×BLUE + 1)",
    min: -1, max: 1,
    goodRange: [0.2, 0.8],
    unit: "",
    gradient: "linear-gradient(to right, #8B0000, #FF6347, #FFFF00, #90EE90, #228B22, #004000)",
    ticks: ["-1.0", "-0.5", "0.0", "0.5", "1.0"],
  },
  MNDWI: {
    label: "MNDWI",
    fullName: "Modified Normalized Difference Water Index",
    description: "Detects open water bodies and soil moisture. Positive values suggest water presence.",
    formula: "(GREEN − SWIR1) / (GREEN + SWIR1)",
    min: -1, max: 1,
    goodRange: [-0.3, 0.0],
    unit: "",
    gradient: "linear-gradient(to right, #8B4513, #F5DEB3, #FFFACD, #87CEEB, #1E90FF, #00008B)",
    ticks: ["-1.0", "-0.5", "0.0", "0.5", "1.0"],
  },
  SAVI: {
    label: "SAVI",
    fullName: "Soil Adjusted Vegetation Index",
    description: "Minimizes soil brightness influence. Useful for sparsely vegetated areas.",
    formula: "1.5 × (NIR − RED) / (NIR + RED + 0.5)",
    min: -1, max: 1,
    goodRange: [0.2, 0.8],
    unit: "",
    gradient: "linear-gradient(to right, #8B0000, #FF4500, #FFFF00, #ADFF2F, #32CD32, #006400)",
    ticks: ["-1.0", "-0.5", "0.0", "0.5", "1.0"],
  },
  GNDVI: {
    label: "GNDVI",
    fullName: "Green Normalized Difference Vegetation Index",
    description: "Sensitive to chlorophyll concentration. Better than NDVI for detecting nitrogen stress.",
    formula: "(NIR − GREEN) / (NIR + GREEN)",
    min: -1, max: 1,
    goodRange: [0.3, 0.8],
    unit: "",
    gradient: "linear-gradient(to right, #8B0000, #FFD700, #90EE90, #228B22, #004000)",
    ticks: ["-1.0", "-0.5", "0.0", "0.5", "1.0"],
  },
  GCI: {
    label: "GCI",
    fullName: "Green Chlorophyll Index",
    description: "Estimates total chlorophyll content in leaves. Higher values = more chlorophyll.",
    formula: "(NIR / GREEN) − 1",
    min: 0, max: 10,
    goodRange: [2.0, 7.0],
    unit: "",
    gradient: "linear-gradient(to right, #FFFACD, #ADFF2F, #32CD32, #228B22, #006400)",
    ticks: ["0", "2.5", "5.0", "7.5", "10"],
  },
  SIPI: {
    label: "SIPI",
    fullName: "Structure Insensitive Pigment Index",
    description: "Ratio of carotenoids to chlorophyll a. High values indicate stress or senescence.",
    formula: "(NIR − BLUE) / (NIR − RED)",
    min: 0, max: 2,
    goodRange: [1.0, 1.8],
    unit: "",
    gradient: "linear-gradient(to right, #006400, #90EE90, #FFD700, #FF8C00, #FF0000)",
    ticks: ["0.0", "0.5", "1.0", "1.5", "2.0"],
  },
  NBR: {
    label: "NBR",
    fullName: "Normalized Burn Ratio",
    description: "Identifies burned areas and fire severity. Negative values indicate burned land.",
    formula: "(NIR − SWIR2) / (NIR + SWIR2)",
    min: -1, max: 1,
    goodRange: [0.1, 0.8],
    unit: "",
    gradient: "linear-gradient(to right, #FF0000, #FF8C00, #FFFF00, #90EE90, #228B22, #006400)",
    ticks: ["-1.0", "-0.5", "0.0", "0.5", "1.0"],
  },
  MGRVI: {
    label: "MGRVI",
    fullName: "Modified Green Red Vegetation Index",
    description: "Discriminates vegetation from soil. Sensitive to green biomass changes.",
    formula: "(GREEN² − RED²) / (GREEN² + RED²)",
    min: -1, max: 1,
    goodRange: [0.0, 0.6],
    unit: "",
    gradient: "linear-gradient(to right, #8B0000, #FF6347, #FFFACD, #90EE90, #228B22, #004000)",
    ticks: ["-1.0", "-0.5", "0.0", "0.5", "1.0"],
  },
  NDWI: {
    label: "NDWI",
    fullName: "Normalized Difference Water Index",
    description: "Detects water content in leaves and water bodies. Negative = dry, Positive = wet.",
    formula: "(GREEN − NIR) / (GREEN + NIR)",
    min: -1, max: 1,
    goodRange: [-0.3, 0.0],
    unit: "",
    gradient: "linear-gradient(to right, #8B4513, #DEB887, #FFFACD, #87CEEB, #1E90FF, #00008B)",
    ticks: ["-1.0", "-0.5", "0.0", "0.5", "1.0"],
  },
};

function renderLegend(indexKey) {
  const cfg = INDEX_CONFIG[indexKey];
  if (!cfg) return;

  document.getElementById("legendTitle").textContent = `${cfg.label} — Legend`;
  document.getElementById("legendGradient").style.background = cfg.gradient;

  const ticksEl = document.getElementById("legendTicks");
  ticksEl.innerHTML = cfg.ticks.map(t => `<span>${t}</span>`).join("");

  document.getElementById("legendDesc").textContent = cfg.description;
  document.getElementById("panelLegend").classList.remove("hidden");
}

function getIndexConfig(key) {
  return INDEX_CONFIG[key] || null;
}

function getHealthColor(value, indexKey) {
  const cfg = INDEX_CONFIG[indexKey];
  if (!cfg) return "#52b788";
  const [lo, hi] = cfg.goodRange;
  if (value < lo) return "#e74c3c";
  if (value > hi) return "#3498db";
  return "#52b788";
}
