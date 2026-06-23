"""
TerraGIS Backend  |  indices.py
──────────────────────────────────────────────────────────────
All 12 spectral index calculations using Google Earth Engine.
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

def _lswi(img):
    """(NIR − SWIR1) / (NIR + SWIR1)  — canopy / surface water content"""
    return img.normalizedDifference(["B8", "B11"]).rename("index")


# ══════════════════════════════════════════════════════════════
#  INDEX CONFIGURATION TABLE
# ══════════════════════════════════════════════════════════════

INDEX_CONFIGS: dict = {
    # NOTE: "class_breaks" / "class_palette" must mirror the
    # corresponding `classes` array in frontend/js/config.js exactly.
    # The rendered map tile is built from a *discrete* classification
    # of these breakpoints (see _build_classified_vis below) rather
    # than a smooth gradient — a continuous gradient previously let
    # low-end classes (e.g. NDVI water, which sits at the very start
    # of the colour ramp) visually blend into the neighbouring class
    # (bare soil), making them indistinguishable on the map even
    # though the legend listed them as different colours.
    "NDVI": {
        "formula":    _ndvi,
        "disp":       (-0.2, 1.0),
        "class_breaks":  [0, 0.2, 0.4, 0.6, 0.8],
        "class_palette": ["4575b4", "d73027", "fdae61", "fee08b", "66bd63", "1a9850"],
    },
    "NDMI": {
        "formula":    _ndmi,
        "disp":       (-0.5, 0.6),
        "class_breaks":  [-0.3, 0, 0.2, 0.4],
        "class_palette": ["8c510a", "dfc27d", "c7eae5", "35978f", "01665e"],
    },
    "EVI": {
        "formula":    _evi,
        "disp":       (0.0, 0.8),
        "class_breaks":  [0.1, 0.3, 0.5, 0.7],
        "class_palette": ["ffffe5", "d9f0a3", "78c679", "238443", "004529"],
    },
    "MDWI": {
        "formula":    _mdwi,
        "disp":       (-0.5, 0.5),
        "class_breaks":  [-0.3, 0, 0.2],
        "class_palette": ["d01c1f", "fdae61", "abd9e9", "313695"],
    },
    "SAVI": {
        "formula":    _savi,
        "disp":       (-0.2, 1.0),
        "class_breaks":  [0.1, 0.3, 0.5, 0.7],
        "class_palette": ["cd853f", "daa520", "9acd32", "228b22", "006400"],
    },
    "GNDVI": {
        "formula":    _gndvi,
        "disp":       (0.0, 0.9),
        "class_breaks":  [0.2, 0.4, 0.6],
        "class_palette": ["ffffcc", "addd8e", "78c679", "006837"],
    },
    "GCI": {
        "formula":    _gci,
        "disp":       (0.0, 10.0),
        "class_breaks":  [1, 3, 5, 7],
        "class_palette": ["ffffe5", "d9f0a3", "78c679", "238443", "006837"],
    },
    "SIPI": {
        "formula":    _sipi,
        "disp":       (0.8, 1.8),
        "class_breaks":  [1.0, 1.3, 1.6],
        "class_palette": ["d53e4f", "f46d43", "e6f598", "3288bd"],
    },
    "NBR": {
        "formula":    _nbr,
        "disp":       (-0.5, 1.0),
        "class_breaks":  [-0.1, 0.1, 0.3, 0.6],
        "class_palette": ["c0392b", "e67e22", "f1c40f", "2ecc71", "1a5276"],
    },
    "MGRVI": {
        "formula":    _mgrvi,
        "disp":       (-0.3, 0.8),
        "class_breaks":  [0, 0.2, 0.4],
        "class_palette": ["d73027", "fdae61", "a6d96a", "1a9850"],
    },
    "NDWI": {
        "formula":    _ndwi,
        "disp":       (-0.5, 0.5),
        "class_breaks":  [-0.3, 0, 0.2, 0.5],
        "class_palette": ["d7191c", "fdae61", "abd9e9", "2c7bb6", "054e9e"],
    },
    "LSWI": {
        "formula":    _lswi,
        "disp":       (-0.5, 0.6),
        "class_breaks":  [-0.2, 0, 0.2, 0.4],
        "class_palette": ["a52a2a", "deb887", "c7eae5", "35978f", "01665e"],
    },
}


BUILTUP_COLOR = "707070"  # matches frontend config.js NDVI "Built-up / Non-Veg" swatch

def _build_classified_vis(
    index_image: "ee.Image",
    cfg: dict,
    water_mask: "ee.Image" = None,
    geometry: "ee.Geometry" = None,
) -> "ee.Image":
    """
    Buckets the continuous index image into the same discrete classes
    shown in the frontend legend, then returns a renderable image whose
    palette is keyed 1:1 to those class colours. Using a discrete
    classification (instead of a continuous gradient) guarantees the
    rendered map tile always agrees with the legend — no two classes
    can blur into each other at a shared boundary.

    NDVI's lowest bucket (value < 0) lumps water and built-up/bare
    surfaces together, since both can read as near-zero or negative
    NDVI. When `water_mask` (MNDWI: (Green−SWIR1)/(Green+SWIR1)) is
    given, that bottom bucket is split using it — true water bodies
    have MNDWI >= 0, built-up/bare surfaces don't — so built-up no
    longer renders as "water" on the map.
    """
    breaks  = cfg["class_breaks"]
    palette = cfg["class_palette"]

    class_id = ee.Image.constant(0)
    for b in breaks:
        class_id = class_id.add(index_image.gte(b))

    if water_mask is not None:
        # .unmask() guarantees the test below is never itself masked —
        # ee.Image.where() propagates a masked *test* pixel straight
        # into the output mask, so a single masked MNDWI pixel (e.g.
        # at a tile edge or partial-resolution mismatch from the 20 m
        # SWIR1 band) was silently dropping pixels from the rendered
        # classification, even though the base NDVI pixel was valid.
        water_ok = water_mask.unmask(-1)
        is_water = water_ok.gte(0)

        # NDVI = (NIR-Red)/(NIR+Red) can come back fully masked over
        # very dark/clear water, where both bands are near-zero and the
        # division is ~0/0 — losing the pixel before it's ever bucketed,
        # even though MNDWI (Green/SWIR1) stays well-defined there. That
        # left ponds/lakes rendering as solid grey "No Data" instead of
        # water. Recover those pixels into the lowest bucket using MNDWI
        # alone (ee.Image.where keeps `value`'s mask wherever its test is
        # true, so this unmasks them) before the built-up split below.
        class_id = class_id.where(is_water, ee.Image.constant(0))

        is_builtup = class_id.eq(0).And(is_water.Not())
        class_id   = class_id.add(1).where(is_builtup, 0)
        palette    = [BUILTUP_COLOR] + palette

    # Hard guarantee against any remaining blank/transparent gaps (e.g. a
    # genuine no-data hole even after mosaicking several recent scenes).
    # reduceRegion()-based stats average only over whatever pixels ARE
    # valid, so they can look perfectly normal even when large parts of
    # the AOI are masked — the map tile is the only place that gap is
    # visible. Filling it with an explicit "No Data" colour means the
    # rendered map is never just blank/see-through basemap.
    # unmask() removes ALL masking (including the boundary outside the
    # AOI), so we re-clip to `geometry` afterwards — otherwise the
    # "No Data" fill would bleed across the entire world tile instead of
    # staying confined to the drawn plot.
    NODATA_COLOR = "999999"
    class_id = class_id.unmask(len(palette))
    if geometry is not None:
        class_id = class_id.clip(geometry)
    palette  = palette + [NODATA_COLOR]

    return class_id.visualize(min=0, max=len(palette) - 1, palette=palette)


# ── TRUE / FALSE COLOUR COMPOSITES (ground-truthing) ────────────
# True colour:  B4/B3/B2 (Red/Green/Blue)   — looks like a normal photo
# False colour: B8/B4/B3 (NIR/Red/Green)    — healthy vegetation glows red
COMPOSITE_STRETCH = (0, 3000)  # typical S2 SR reflectance display range

def _build_composite_tile_url(image: "ee.Image", geometry: "ee.Geometry", bands: list) -> str:
    """Renders a 3-band RGB composite (true or false colour) and returns its tile URL."""
    lo, hi = COMPOSITE_STRETCH
    vis = image.clip(geometry).visualize(bands=bands, min=lo, max=hi)
    return vis.getMapId()["tile_fetcher"].url_format


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
    CANDIDATE_LIMIT        = 10
    n_candidates = min(image_count, CANDIDATE_LIMIT)
    candidate_list = collection.toList(n_candidates)

    # Compute AOI coverage + scene date for every candidate server-side,
    # then pull all of it back in a single getInfo() round trip instead
    # of one (or two) round trips per candidate.
    def _candidate_info(img):
        img = ee.Image(img)
        coverage = (
            img.select(0).mask()
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
        return ee.Feature(None, {
            "coverage": coverage,
            "date":     img.date().format("dd MMM YYYY"),
        })

    candidate_info = (
        ee.FeatureCollection(candidate_list.map(_candidate_info))
        .getInfo()["features"]
    )

    image      = None
    scene_date = None
    for i, feat in enumerate(candidate_info):
        props         = feat["properties"]
        coverage_frac = props["coverage"] or 0.0
        if coverage_frac >= MIN_COVERAGE_FRACTION:
            image      = ee.Image(candidate_list.get(i))
            scene_date = props["date"]
            logger.info(f"[{label}] Using scene {i} — AOI coverage {coverage_frac:.0%}")
            break

    if image is None:
        image      = ee.Image(candidate_list.get(0))
        scene_date = candidate_info[0]["properties"]["date"]
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
          true_color_url,            — RGB (B4/B3/B2) composite tile URL
          false_color_url,           — NIR/Red/Green (B8/B4/B3) composite tile URL
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
    # NOTE: classification tiles are rendered straight off the native
    # 10 m pixels (no .resample()). Bilinear resampling was tried here
    # to smooth the rendered tile, but it has repeatedly caused the
    # classification to render fully/partially blank or grey ("No
    # Data") at render time even while reduceRegion()-based stats
    # stayed completely normal — resample() needs a single well-defined
    # projection to interpolate against, and silently fails closed
    # (fully masked output) whenever that's not satisfied. Discrete
    # classification doesn't need smoothing anyway, so we just drop it.
    index_image = cfg["formula"](image).clip(geometry)
    index_image_vis = index_image

    # ── Diagnostics: raw surface-reflectance band means over the AOI ──
    # Logged so an apparently-wrong classification (e.g. low NDVI over
    # visibly dense canopy) can be root-caused from real numbers — a
    # low NIR mean with a normal Red mean points at a masking/band
    # bug, not a seasonal/lighting effect, and vice versa.
    try:
        band_means = (
            image.select(["B2", "B3", "B4", "B8", "B11"])
            .clip(geometry)
            .reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geometry,
                scale=10,
                bestEffort=True,
                maxPixels=1e10,
            )
            .getInfo()
        )
        logger.info(f"[{index_key}] Raw band means (SR DN, ×0.0001=reflectance) over AOI: {band_means}")
    except Exception:
        logger.exception(f"[{index_key}] band-mean diagnostic failed")

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

    # ── Map tile URL (discrete classification matching the legend) ─
    # NDVI: disambiguate water vs built-up within the lowest bucket
    # using MNDWI, so built-up areas stop rendering as "water". If the
    # extra MNDWI computation ever fails (e.g. exotic scene/geometry
    # combinations), fall back to the plain classification rather than
    # surfacing a blank map.
    try:
        water_mask = _mdwi(image).clip(geometry) if index_key == "NDVI" else None
        map_id     = _build_classified_vis(index_image_vis, cfg, water_mask, geometry).getMapId()
    except Exception:
        logger.exception(f"[{index_key}] water/built-up split failed — falling back to plain classification")
        try:
            map_id = _build_classified_vis(index_image_vis, cfg, geometry=geometry).getMapId()
        except Exception:
            # Last-resort fallback: render the raw continuous index with a
            # simple linear stretch so the map is NEVER left blank, even if
            # the discrete classification pipeline itself is broken.
            logger.exception(f"[{index_key}] plain classification also failed — falling back to continuous stretch")
            map_id = (
                index_image_vis
                .unmask((dmin + dmax) / 2)
                .clip(geometry)
                .visualize(min=dmin, max=dmax, palette=cfg["class_palette"])
                .getMapId()
            )
    tile_url = map_id["tile_fetcher"].url_format
    # url_format already contains {z}/{x}/{y} placeholders — ready for Leaflet

    # ── True / false colour composites for ground-truthing ─────
    # Rendered from the same selected scene so they line up exactly
    # with the classification overlay above.
    try:
        true_color_url  = _build_composite_tile_url(image, geometry, ["B4", "B3", "B2"])
        false_color_url = _build_composite_tile_url(image, geometry, ["B8", "B4", "B3"])
    except Exception:
        logger.exception(f"[{index_key}] composite tile generation failed")
        true_color_url = false_color_url = None

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
        "tile_url":         tile_url,
        "true_color_url":   true_color_url,
        "false_color_url":  false_color_url,
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
