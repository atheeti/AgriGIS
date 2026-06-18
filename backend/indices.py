"""
TerraGIS Backend  |  indices.py
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

logger = logging.getLogger("terragis.indices")

# Fixed acquisition constraints — no longer user-configurable from the UI.
# We always take the most recent Sentinel-2 scene with <=5% cloud cover,
# searching back far enough that one is virtually always available.
MAX_CLOUD_PERCENT  = 5
SEARCH_WINDOW_DAYS = 90


# ══════════════════════════════════════════════════════════════
#  CLOUD MASKING
# ══════════════════════════════════════════════════════════════

CLOUD_PROB_THRESHOLD = 50  # s2cloudless probability (%) above which a pixel is masked as cloud

# SCL (Scene Classification Layer) classes to mask out:
#   3  = cloud shadow
#   8  = cloud, medium probability
#   9  = cloud, high probability
#   10 = thin cirrus
#   11 = snow / ice
_SCL_MASKED_CLASSES = [3, 8, 9, 10, 11]


def _mask_s2_clouds(image: ee.Image) -> ee.Image:
    """
    Remove cloudy / shadowed pixels using two complementary signals:
      1. The Scene Classification Layer (SCL band, 20 m) — masks cloud
         shadow, medium/high probability cloud, thin cirrus and snow.
      2. The s2cloudless per-pixel cloud probability band (joined onto
         each image as "s2cloudless" by _select_scene) — masks any
         pixel whose cloud probability exceeds CLOUD_PROB_THRESHOLD.
    Combining both is far more accurate than the coarse QA60 bitmask,
    which only flags clouds at 60 m resolution and misses thin cirrus
    and cloud shadow entirely.
    """
    scl      = image.select("SCL")
    scl_mask = scl.remap(_SCL_MASKED_CLASSES, [0] * len(_SCL_MASKED_CLASSES), 1).eq(1)

    cloud_prob = ee.Image(image.get("s2cloudless")).select("probability")
    prob_mask  = cloud_prob.lt(CLOUD_PROB_THRESHOLD)

    return (
        image
        .updateMask(scl_mask.And(prob_mask))
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

def _select_scene(geometry: "ee.Geometry", label: str = ""):
    """
    Shared scene-selection logic used by both calculate() and
    cross_section(). Picks the newest Sentinel-2 scene (<=MAX_CLOUD_PERCENT
    global cloud cover) where most of `geometry` is actually unmasked
    after local QA60 cloud masking.

    Returns (image, scene_date, image_count). Raises ValueError if no
    scene is found at all.
    """
    today = datetime.now(timezone.utc)
    start = today - timedelta(days=SEARCH_WINDOW_DAYS)
    start_str = start.strftime("%Y-%m-%d")
    end_str   = today.strftime("%Y-%m-%d")

    s2_sr = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geometry)
        .filterDate(start_str, end_str)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_PERCENT))
    )

    s2_cloud_prob = (
        ee.ImageCollection("COPERNICUS/S2_CLOUD_PROBABILITY")
        .filterBounds(geometry)
        .filterDate(start_str, end_str)
    )

    # Attach the matching s2cloudless probability image to each SR scene
    # (by shared system:index) so _mask_s2_clouds can read it via
    # image.get("s2cloudless").
    s2_joined = ee.Join.saveFirst("s2cloudless").apply(
        primary=s2_sr,
        secondary=s2_cloud_prob,
        condition=ee.Filter.equals(leftField="system:index", rightField="system:index"),
    )

    collection = (
        ee.ImageCollection(s2_joined)
        .map(_mask_s2_clouds)
        .sort("system:time_start", False)   # newest image first
    )

    image_count = collection.size().getInfo()
    logger.info(
        f"[{label}] {image_count} scene(s) found  "
        f"| {start_str} → {end_str}  | cloud < {MAX_CLOUD_PERCENT}%"
    )

    if image_count == 0:
        raise ValueError(
            f"No clear Sentinel-2 imagery found in the last {SEARCH_WINDOW_DAYS} days "
            f"with less than {MAX_CLOUD_PERCENT}% cloud cover."
        )

    MIN_COVERAGE_FRACTION = 0.6
    image_list  = collection.toList(min(image_count, 10))
    image       = None
    scene_date  = None

    for i in range(image_list.size().getInfo()):
        candidate = ee.Image(image_list.get(i))
        coverage = (
            candidate.select(0).mask()
            .reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=10,
                bestEffort=True,
                maxPixels=1e10,
            )
            .values()
            .get(0)
        )
        coverage_frac = ee.Number(coverage).getInfo() or 0.0
        if coverage_frac >= MIN_COVERAGE_FRACTION:
            image      = candidate
            scene_date = candidate.date().format("dd MMM YYYY").getInfo()
            logger.info(f"[{label}] Using scene {i} — AOI coverage {coverage_frac:.0%}")
            break

    if image is None:
        image      = collection.first()
        scene_date = image.date().format("dd MMM YYYY").getInfo()
        logger.warning(f"[{label}] No scene reached {MIN_COVERAGE_FRACTION:.0%} AOI coverage; using newest available.")

    return image, scene_date, image_count


def calculate(
    index_key:    str,
    geometry_dict: dict,
) -> dict:
    """
    Run a full index analysis on GEE, using the most recent Sentinel-2
    scene available with <=MAX_CLOUD_PERCENT cloud cover.

    Args:
        index_key:     Spectral index name (e.g. "NDVI")
        geometry_dict: GeoJSON geometry {type, coordinates}

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

    # ── Scene selection (newest clear scene, AOI-coverage aware) ──
    image, scene_date, image_count = _select_scene(geometry, label=index_key)

    # ── Index computation ──────────────────────────────────────
    # .resample('bilinear') smooths pixel-to-pixel transitions in the
    # rendered tile (sharper-looking map) without altering the native
    # 10 m statistics, which are still reduced from the unresampled image.
    index_image = cfg["formula"](image).clip(geometry)
    index_image_vis = index_image.resample("bilinear")

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
    # ee.Reducer.combine() suffixes EVERY output with its statistic name
    # (e.g. "index_mean", not bare "index") once more than one reducer is
    # combined — read the mean from "index_mean", falling back to "index"
    # for single-reducer cases.
    mean_key = "index_mean" if "index_mean" in stats_raw else "index"

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
    map_id   = index_image_vis.getMapId(cfg["vis_params"])
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
        "mean":        _safe(stats_raw.get(mean_key)),
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


# ══════════════════════════════════════════════════════════════
#  CROSS-SECTION ANALYSIS
#  Samples the index value of every ~10 m pixel along a user-drawn
#  line, for plotting a distance-vs-index line graph on the frontend.
# ══════════════════════════════════════════════════════════════

_PIXEL_SPACING_M = 10
_MAX_LINE_SAMPLES = 300


def _interpolate_line_points(coords: list, spacing_m: float = _PIXEL_SPACING_M, max_points: int = _MAX_LINE_SAMPLES):
    """
    Evenly re-samples a [[lon, lat], ...] polyline at `spacing_m` Sentinel-2
    pixel intervals using Haversine great-circle distance.
    Returns [(lon, lat, distance_from_start_m), ...].
    """
    def _hav(p1, p2):
        R = 6371000.0
        lon1, lat1 = p1
        lon2, lat2 = p2
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlmb = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
        return 2 * R * math.asin(math.sqrt(a))

    seg_lens = [_hav(coords[i], coords[i + 1]) for i in range(len(coords) - 1)]
    total = sum(seg_lens)
    if total == 0:
        return [(coords[0][0], coords[0][1], 0.0)]

    n = min(max_points, max(2, int(total / spacing_m) + 1))
    targets = [total * i / (n - 1) for i in range(n)]

    points  = []
    cum     = 0.0
    seg_idx = 0
    for t in targets:
        while seg_idx < len(seg_lens) - 1 and cum + seg_lens[seg_idx] < t:
            cum += seg_lens[seg_idx]
            seg_idx += 1
        seg_len = seg_lens[seg_idx] or 1e-9
        frac    = max(0.0, min(1.0, (t - cum) / seg_len))
        lon1, lat1 = coords[seg_idx]
        lon2, lat2 = coords[seg_idx + 1]
        points.append((lon1 + (lon2 - lon1) * frac, lat1 + (lat2 - lat1) * frac, t))
    return points


def cross_section(
    index_key:     str,
    geometry_dict: dict,
    line_coords:   list,
) -> dict:
    """
    Sample the spectral index along a drawn line, one point per
    ~10 m Sentinel-2 pixel.

    Args:
        index_key:     Spectral index name (e.g. "NDVI")
        geometry_dict: GeoJSON polygon of the analysed plot (used to pick
                        the same Sentinel-2 scene as /api/calculate)
        line_coords:   [[lon, lat], ...] — the drawn cross-section line

    Returns:
        { scene_date, points: [{distance, value, lat, lon}, ...] }
    """
    cfg      = INDEX_CONFIGS[index_key]
    geometry = ee.Geometry(geometry_dict)

    image, scene_date, _ = _select_scene(geometry, label=f"{index_key}-xsection")
    index_image = cfg["formula"](image)

    samples  = _interpolate_line_points(line_coords)
    features = [
        ee.Feature(ee.Geometry.Point(lon, lat), {"idx": i})
        for i, (lon, lat, _dist) in enumerate(samples)
    ]
    fc = ee.FeatureCollection(features)

    sampled = index_image.sampleRegions(
        collection=fc,
        scale=10,
        geometries=False,
    ).getInfo()

    by_idx = {f["properties"]["idx"]: f["properties"].get("index") for f in sampled["features"]}

    def _clean(v):
        if v is None:
            return None
        try:
            f = float(v)
            return None if math.isnan(f) else f
        except (TypeError, ValueError):
            return None

    points = [
        {
            "distance": round(dist, 1),
            "value":    _clean(by_idx.get(i)),
            "lat":      lat,
            "lon":      lon,
        }
        for i, (lon, lat, dist) in enumerate(samples)
    ]

    logger.info(f"[{index_key}-xsection] Sampled {len(points)} points along line | scene={scene_date}")

    return {"scene_date": scene_date, "points": points}
