"""
TerraGIS Backend  |  schemas.py
Pydantic models for request validation and response serialisation.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List


class CalculateRequest(BaseModel):
    """POST /api/calculate — body schema."""

    index: str = Field(
        ...,
        description="Spectral index key",
        examples=["NDVI"],
    )
    geometry: Dict[str, Any] = Field(
        ...,
        description="GeoJSON geometry object (type + coordinates)",
    )


class CrossSectionRequest(BaseModel):
    """POST /api/cross-section — body schema."""

    index: str = Field(
        ...,
        description="Spectral index key",
        examples=["NDVI"],
    )
    geometry: Dict[str, Any] = Field(
        ...,
        description="GeoJSON polygon of the analysed plot (used to pick the scene)",
    )
    line: List[List[float]] = Field(
        ...,
        description="Cross-section line as [[lon, lat], ...] coordinates",
    )


class HistogramBin(BaseModel):
    center: float
    count:  int


class CalculateResponse(BaseModel):
    """POST /api/calculate — response schema."""

    mean:         float
    min:          float
    max:          float
    std:          float
    scene_date:   str
    tile_url:     str
    histogram:    List[HistogramBin]
    image_count:  int
