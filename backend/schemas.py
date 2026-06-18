"""
AgriGIS Backend  |  schemas.py
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
    days_back: int = Field(
        default=30,
        ge=1,
        le=365,
        description="Days to search backwards from today",
    )
    max_cloud: int = Field(
        default=20,
        ge=0,
        le=100,
        description="Maximum acceptable cloud cover percentage",
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
