"""
TerraGIS Backend  |  main.py
FastAPI application — serves both the REST API and the frontend static files.

Run:
    cd backend
    uvicorn main:app --reload --port 8000

Then open:  http://localhost:8000
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from services import gee_auth
from routes.api import router as api_router

# ── LOGGING ───────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("terragis")


# ── STARTUP / SHUTDOWN ────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize Google Earth Engine when the server starts."""
    logger.info("━" * 50)
    logger.info("  TerraGIS Backend starting…")
    try:
        gee_auth.initialize()
        logger.info("  ✓ Google Earth Engine ready")
    except Exception as exc:
        logger.error(f"  ✗ GEE init failed: {exc}")
        logger.warning("  /api/calculate will be unavailable until GEE is configured.")
    logger.info("  Open http://localhost:8000 in your browser")
    logger.info("━" * 50)
    yield
    logger.info("TerraGIS Backend shutting down.")


# ── APP ───────────────────────────────────────────────────────
app = FastAPI(
    title="TerraGIS API",
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

# API routes must be registered BEFORE the static-file mount below.
app.include_router(api_router)


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
