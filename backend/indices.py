"""
AgriGIS Backend  |  indices.py
──────────────────────────────────────────────────────────────
All 11 spectral index calculations using Google Earth Engine.
Collection: COPERNICUS/S2_SR_HARMONIZED (10 m, surface reflectance)

Band mapping:
  B2  Blue  490 nm    B3  Green  560 nm    B4  Red    665 nm
  B8  NIR   842 nm    B8A RedEdge 865 nm   B11 SWIR1 1610 nm
  B12 SWIR2 2190 nm

Scale factor: raw DN × 0.0001 = surface reflectance (0–1).
  → Normalised-difference indices don't need explicit scaling
    (the 0.0001 factor cancels in numerator/denominator).
  → EVI and SAVI need explicit scaling due to additive constants.
"""

import ee
import math
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("agrigis.indices")


# ══════════════════════════════════════════════════════════════
#  CLOUD MASKING
# ══════════════════════════════════════════════════════════════

def _mask_s2_clouds(image: ee.Image) -> ee.Image:
    """
    Remove cloudy pixels using the Sentinel-2 QA60 bitmask.
      Bit 10 = opaque clouds
      Bit 11 = cirrus clouds
    Pixels where either bit is set are masked out.
    """
    qa           = image.select("QA60")
    cloud_mask   = qa.bitwiseAnd(1 << 10).eq(0)
    cirrus_mask  = qa.bitwiseAnd(1 << 11).eq(0)
    return (
        image
        .updateMask(cloud_mask.And(cirrus_mask))
        .copyProperties(image, ["system:time_start"])
    )


# ══════════════════════════════════════════════════════════════
#  INDEX FORMULA FUNCTIONS
#  Each returns a single-band ee.Image named "index".
# ══════════════════════════════════════════════════════════════

def _ndvi(img):
    """(NIR − Red) / (NIR + Red)"""
    return img.normalizedDifference(["B8", "B4"]).rename("index")

def _ndmi(img):
    """(NIR − SWIR1) / (NIR + SWIR1)"""
    return img.normalizedDifference(["B8", "B11"]).rename("index")

def _evi(img):
    """2.5 × (NIR−Red) / (NIR + 6·Red − 7.5·Blue + 1)  — needs reflectance"""
    s = img.multiply(0.0001)
    return s.expression(
        "2.5 * (NIR - RED) / (NIR + 6.0 * RED - 7.5 * BLUE + 1.0)",
        {"NIR": s.select("B8"), "RED": s.select("B4"), "BLUE": s.select("B2")},
    ).rename("index")

def _mdwi(img):
    """(Green − SWIR1) / (Green + SWIR1)"""
    return img.normalizedDifference(["B3", "B11"]).rename("index")

def _savi(img):
    """((NIR − Red) / (NIR + Red + 0.5)) × 1.5  — needs reflectance"""
    s = img.multiply(0.0001)
    return s.expression(
        "((NIR - RED) / (NIR + RED + 0.5)) * 1.5",
        {"NIR": s.select("B8"), "RED": s.select("B4")},
    ).rename("index")

def _gndvi(img):
    """(NIR − Green) / (NIR + Green)"""
    return img.normalizedDifference(["B8", "B3"]).rename("index")

def _gci(img):
    """(NIR / Green) − 1  — scale cancels in ratio"""
    return img.select("B8").divide(img.select("B3")).subtract(1).rename("index")

def _sipi(img):
    """(NIR − Blue) / (NIR − Red)  — scale cancels"""
    num = img.select("B8").subtract(img.select("B2"))
    den = img.select("B8").subtract(img.select("B4")).abs().max(ee.Image(1e-6))
    return num.divide(den).rename("index")

def _nbr(img):
    """(NIR − SWIR2) / (NIR + SWIR2)  uses B8A + B12"""
    return img.normalizedDifference(["B8A", "B12"]).rename("index")

def _mgrvi(img):
    """(Green² − Red²) / (Green² + Red²)  — scale² cancels"""
    g2 = img.select("B3").pow(2)
    r2 = img.select("B4").pow(2)
    return g2.subtract(r2).divide(g2.add(r2).max(ee.Image(1e-10))).rename("index")

def _ndwi(img):
    """(Green − NIR) / (Green + NIR)"""
    return img.normalizedDifference(["B3", "B8"]).rename("index")


# ══════════════════════════════════════════════════════════════
#  INDEX CONFIGURATION TABLE
# ══════════════════════════════════════════════════════════════

INDEX_CONFIGS: dict = {
    "NDVI": {
        "formula":    _ndvi,
        "disp":       (-0.2, 1.0),
        "vis_params": {
            "min": -0.2, "max": 1.0,
            "palette": ["d73027","f46d43","fdae61","fee08b","ffffbf","d9ef8b","a6d96a","66bd63","1a9850"],
        },
    },
    "NDMI": {
        "formula":    _ndmi,
        "disp":       (-0.5, 0.6),
        "vis_params": {
            "min": -0.5, "max": 0.6,
            "palette": ["8c510a","bf812d","dfc27d","f5f5f5","c7eae5","80cdc1","35978f","01665e"],
        },
    },
    "EVI": {
        "formula":    _evi,
        "disp":       (0.0, 0.8),
        "vis_params": {
            "min": 0.0, "max": 0.8,
            "palette": ["ffffe5","f7fcb9","d9f0a3","addd8e","78c679","41ab5d","238443","006837","004529"],
        },
    },
    "MDWI": {
        "formula":    _mdwi,
        "disp":       (-0.5, 0.5),
        "vis_params": {
            "min": -0.5, "max": 0.5,
            "palette": ["d01c1f","f46d43","fdae61","ffffbf","abd9e9","74add1","4575b4","313695"],
        },
    },
    "SAVI": {
        "formula":    _savi,
        "disp":       (-0.2, 1.0),
        "vis_params": {
            "min": -0.2, "max": 1.0,
            "palette": ["8b4513","cd853f","daa520","ffd700","9acd32","32cd32","228b22","006400"],
        },
    },
    "GNDVI": {
        "formula":    _gndvi,
        "disp":       (0.0, 0.9),
        "vis_params": {
            "min": 0.0, "max": 0.9,
            "palette": ["ffffcc","d9f0a3","addd8e","78c679","41ab5d","238443","006837"],
        },
    },
    "GCI": {
        "formula":    _gci,
        "disp":       (0.0, 10.0),
        "vis_params": {
            "min": 0.0, "max": 10.0,
            "palette": ["ffffe5","f7fcb9","d9f0a3","addd8e","78c679","41ab5d","238443","006837"],
        },
    },
    "SIPI": {
        "formula":    _sipi,
        "disp":       (0.8, 1.8),
        "vis_params": {
            "min": 0.8, "max": 1.8,
            "palette": ["9e0142","d53e4f","f46d43","fdae61","ffffbf","e6f598","abdda4","66c2a5","3288bd"],
        },
    },
    "NBR": {
        "formula":    _nbr,
        "disp":       (-0.5, 1.0),
        "vis_params": {
            "min": -0.5, "max": 1.0,
            "palette": ["7b2d00","c0392b","e67e22","f1c40f","2ecc71","27ae60","1a5276"],
        },
    },
    "MGRVI": {
        "formula":    _mgrvi,
        "disp":       (-0.3, 0.8),
        "vis_params": {
            "min": -0.3, "max": 0.8,
            "palette": ["a50026","d73027","fdae61","ffffbf","a6d96a","1a9850"],
        },
    },
    "NDWI": {
        "formula":    _ndwi,
        "disp":       (-0.5, 0.5),
        "vis_params": {
            "min": -0.5, "max": 0.5,
            "palette": ["d7191c","fdae61","ffffbf","abd9e9","2c7bb6","054e9e"],
        },
    },
}


# ══════════════════════════════════════════════════════════════
#  MAIN CALCULATION FUNCTION
# ══════════════════════════════════════════════════════════════

def calculate(
    index_key:    str,
    geometry_dict: dict,
    days_back:    int,
    max_cloud:    int,
) -> dict:
    """
    Run a full index analysis on GEE.

    Args:
        index_key:     Spectral index name (e.g. "NDVI")
        geometry_dict: GeoJSON geometry {type, coordinates}
        days_back:     Number of days to search backwards from today
        max_cloud:     Max acceptable cloud cover (0–100 %)

    Returns:
        {
          mean, min, max, std,       — float statistics
          scene_date,                — "DD Mon YYYY"
          tile_url,                  — Leaflet-compatible URL from GEE
          histogram,                 — [{center, count}, …]  20 bins
          image_count,               — number of scenes found
        }

    Raises:
        ValueError  if no valid imagery found
        Exception   for GEE computation errors
    """
    cfg        = INDEX_CONFIGS[index_key]
    dmin, dmax = cfg["disp"]

    # ── Geometry ───────────────────────────────────────────────
    geometry = ee.Geometry(geometry_dict)

    # ── Date range ─────────────────────────────────────────────
    today = datetime.now(timezone.utc)
    start = today - timedelta(days=days_back)
    start_str = start.strftime("%Y-%m-%d")
    end_str   = today.strftime("%Y-%m-%d")

    # ── Sentinel-2 collection ──────────────────────────────────
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geometry)
        .filterDate(start_str, end_str)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", max_cloud))
        .map(_mask_s2_clouds)
        .sort("CLOUDY_PIXEL_PERCENTAGE")   # best (clearest) image first
    )

    image_count = collection.size().getInfo()
    logger.info(
        f"[{index_key}] {image_count} scene(s) found  "
        f"| {start_str} → {end_str}  | cloud < {max_cloud}%"
    )

    if image_count == 0:
        raise ValueError(
            f"No clear Sentinel-2 imagery found in the last {days_back} days "
            f"with less than {max_cloud}% cloud cover. "
            f"Try a wider date range or a higher cloud cover limit."
        )

    image      = collection.first()
    scene_date = image.date().format("dd MMM YYYY").getInfo()

    # ── Index computation ──────────────────────────────────────
    index_image = cfg["formula"](image).clip(geometry)

    # ── Statistics (combined reducer → one server roundtrip) ───
    stats_raw = index_image.reduceRegion(
        reducer=(
            ee.Reducer.mean()
            .combine(ee.Reducer.min(),    sharedInputs=True)
            .combine(ee.Reducer.max(),    sharedInputs=True)
            .combine(ee.Reducer.stdDev(), sharedInputs=True)
        ),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e10,
    ).getInfo()
    # Output keys: "index", "index_min", "index_max", "index_stdDev"

    # ── Histogram (20 equal bins) ──────────────────────────────
    hist_raw = index_image.reduceRegion(
        reducer=ee.Reducer.fixedHistogram(dmin, dmax, 20),
        geometry=geometry,
        scale=10,
        bestEffort=True,
        maxPixels=1e10,
    ).getInfo()

    raw_bins  = hist_raw.get("index", [])
    bin_width = (dmax - dmin) / 20
    histogram = [
        {"center": round(b[0] + bin_width / 2, 5), "count": int(b[1])}
        for b in raw_bins
    ]

    # ── Map tile URL ───────────────────────────────────────────
    map_id   = index_image.getMapId(cfg["vis_params"])
    tile_url = map_id["tile_fetcher"].url_format
    # url_format already contains {z}/{x}/{y} placeholders — ready for Leaflet

    # ── Clean up NaN / None ────────────────────────────────────
    def _safe(v, default=0.0) -> float:
        if v is None:
            return default
        try:
            f = float(v)
            return default if math.isnan(f) else f
        except (TypeError, ValueError):
            return default

    result = {
        "mean":        _safe(stats_raw.get("index")),
        "min":         _safe(stats_raw.get("index_min")),
        "max":         _safe(stats_raw.get("index_max")),
        "std":         _safe(stats_raw.get("index_stdDev")),
        "scene_date":  scene_date,
        "tile_url":    tile_url,
        "histogram":   histogram,
        "image_count": image_count,
    }

    logger.info(
        f"[{index_key}] Done — mean={result['mean']:.4f}  "
        f"min={result['min']:.4f}  max={result['max']:.4f}  "
        f"scene={scene_date}"
    )
    return result
