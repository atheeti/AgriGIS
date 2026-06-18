"""
AgriGIS Backend  |  main.py
FastAPI application — serves both the REST API and the frontend static files.

Run:
    cd backend
    uvicorn main:app --reload --port 8000

Then open:  http://localhost:8000
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

import gee_auth
import indices
from schemas import CalculateRequest

# ── LOGGING ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("agrigis")


# ── STARTUP / SHUTDOWN ────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Google Earth Engine when the server starts."""
    logger.info("━" * 50)
    logger.info("  AgriGIS Backend starting…")
    try:
        gee_auth.initialize()
        logger.info("  ✓ Google Earth Engine ready")
    except Exception as exc:
        logger.error(f"  ✗ GEE init failed: {exc}")
        logger.warning("  /api/calculate will be unavailable until GEE is configured.")
    logger.info("  Open http://localhost:8000 in your browser")
    logger.info("━" * 50)
    yield
    logger.info("AgriGIS Backend shutting down.")


# ── APP ───────────────────────────────────────────────────────
app = FastAPI(
    title="AgriGIS API",
    description="Crop health intelligence — Google Earth Engine + Sentinel-2",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Allow the frontend (running on any port during dev) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ══════════════════════════════════════════════════════════════
#  API ROUTES  (must be registered BEFORE the static-file mount)
# ══════════════════════════════════════════════════════════════

@app.get("/api/health", tags=["system"])
async def health():
    """
    Health check.
    The frontend polls this on load to know if the backend + GEE are ready.
    """
    return {
        "status":    "ok",
        "gee_ready": gee_auth.is_ready(),
        "version":   "1.0.0",
    }


@app.get("/api/indices", tags=["indices"])
async def list_indices():
    """Return the names of all supported spectral indices."""
    return {"indices": list(indices.INDEX_CONFIGS.keys())}


@app.post("/api/calculate", tags=["indices"])
async def calculate(req: CalculateRequest):
    """
    Calculate a spectral index for a drawn polygon.

    - **index**    : e.g. "NDVI", "EVI", "NDWI"
    - **geometry** : GeoJSON geometry (type + coordinates)
    - **days_back**: how many days of imagery to search
    - **max_cloud**: maximum acceptable cloud cover (%)

    Returns statistics, a 20-bin histogram, and a Leaflet tile URL
    pointing to the classified index map served directly by GEE.
    """
    if not gee_auth.is_ready():
        raise HTTPException(
            status_code=503,
            detail="Google Earth Engine is not initialised. Check backend logs and your .env file.",
        )

    if req.index not in indices.INDEX_CONFIGS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown index '{req.index}'. Supported: {list(indices.INDEX_CONFIGS.keys())}",
        )

    try:
        result = indices.calculate(
            index_key=req.index,
            geometry_dict=req.geometry,
            days_back=req.days_back,
            max_cloud=req.max_cloud,
        )
        return JSONResponse(content=result)

    except ValueError as exc:
        # No imagery found, bad geometry, etc.
        raise HTTPException(status_code=404, detail=str(exc))

    except Exception as exc:
        logger.exception("Unhandled calculation error")
        raise HTTPException(status_code=500, detail=f"Earth Engine error: {exc}")


# ══════════════════════════════════════════════════════════════
#  SERVE FRONTEND  (catch-all — must come LAST)
# ══════════════════════════════════════════════════════════════

FRONTEND_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "frontend")
)

if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
    logger.info(f"Frontend served from: {FRONTEND_DIR}")
else:
    logger.warning(f"Frontend directory not found at {FRONTEND_DIR}")
