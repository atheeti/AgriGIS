"""
TerraGIS Backend  |  routes/api.py
API routes — health, index listing, calculate, cross-section.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from services import gee_auth, indices
from models.schemas import CalculateRequest, CrossSectionRequest

logger = logging.getLogger("terragis")

router = APIRouter()


@router.get("/api/health", tags=["system"])
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


@router.get("/api/indices", tags=["indices"])
async def list_indices():
    """Return the names of all supported spectral indices."""
    return {"indices": list(indices.INDEX_CONFIGS.keys())}


@router.post("/api/calculate", tags=["indices"])
async def calculate(req: CalculateRequest):
    """
    Calculate a spectral index for a drawn polygon.

    - **index**    : e.g. "NDVI", "EVI", "NDWI"
    - **geometry** : GeoJSON geometry (type + coordinates)

    Uses the most recent Sentinel-2 scene available with <=10% cloud cover.
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
        )
        return JSONResponse(content=result)

    except ValueError as exc:
        # No imagery found, bad geometry, etc.
        raise HTTPException(status_code=404, detail=str(exc))

    except Exception as exc:
        logger.exception("Unhandled calculation error")
        raise HTTPException(status_code=500, detail=f"Earth Engine error: {exc}")


@router.post("/api/cross-section", tags=["indices"])
async def cross_section(req: CrossSectionRequest):
    """
    Sample the spectral index value of every ~10 m pixel along a
    user-drawn line, for a distance-vs-index line graph.

    - **index**    : e.g. "NDVI", "EVI", "NDWI"
    - **geometry** : GeoJSON polygon of the analysed plot
    - **line**     : [[lon, lat], ...] coordinates of the drawn line
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

    if len(req.line) < 2:
        raise HTTPException(status_code=400, detail="Line must have at least 2 points.")

    try:
        result = indices.cross_section(
            index_key=req.index,
            geometry_dict=req.geometry,
            line_coords=req.line,
        )
        return JSONResponse(content=result)

    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    except Exception as exc:
        logger.exception("Unhandled cross-section error")
        raise HTTPException(status_code=500, detail=f"Earth Engine error: {exc}")
