from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
import httpx
from services.sentinel import fetch_index_map, fetch_index_stats
from config import INDEX_METADATA

router = APIRouter()

VALID_INDICES = list(INDEX_METADATA.keys())


def get_http_client() -> httpx.AsyncClient:
    from main import http_client
    return http_client


class IndexRequest(BaseModel):
    index: str
    geometry: dict
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    farmer_id: Optional[int] = None

    @field_validator("index")
    @classmethod
    def validate_index(cls, v: str) -> str:
        v = v.upper()
        if v not in VALID_INDICES:
            raise ValueError(f"Invalid index. Choose from: {', '.join(VALID_INDICES)}")
        return v

    @field_validator("date_from", "date_to", mode="before")
    @classmethod
    def set_default_dates(cls, v):
        return v

    def get_dates(self) -> tuple[str, str]:
        today = datetime.utcnow()
        date_to = self.date_to or today.strftime("%Y-%m-%d")
        date_from = self.date_from or (today - timedelta(days=30)).strftime("%Y-%m-%d")
        return date_from, date_to


@router.get("/list")
def list_indices():
    return [
        {
            "key": k,
            "full_name": v["full_name"],
            "description": v["description"],
            "formula": v["formula"],
            "min": v["min"],
            "max": v["max"],
            "colors": v["colors"],
        }
        for k, v in INDEX_METADATA.items()
    ]


@router.post("/map")
async def generate_index_map(
    body: IndexRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
):
    date_from, date_to = body.get_dates()
    try:
        image_data = await fetch_index_map(
            index=body.index,
            geometry=body.geometry,
            date_from=date_from,
            date_to=date_to,
            client=client,
        )
    except httpx.HTTPStatusError as e:
        detail = f"Sentinel Hub error: {e.response.status_code}"
        try:
            detail += f" - {e.response.json().get('message', '')}"
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=detail)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Map generation failed: {str(e)}")

    # Calculate bounds from geometry
    coords = _extract_coords(body.geometry)
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    meta = INDEX_METADATA[body.index]
    return {
        "image_data": image_data,
        "bounds": {
            "south": min(lats),
            "west": min(lngs),
            "north": max(lats),
            "east": max(lngs),
        },
        "index": body.index,
        "full_name": meta["full_name"],
        "date_from": date_from,
        "date_to": date_to,
        "colors": meta["colors"],
        "min": meta["min"],
        "max": meta["max"],
    }


@router.post("/stats")
async def get_index_stats(
    body: IndexRequest,
    client: httpx.AsyncClient = Depends(get_http_client),
):
    date_from, date_to = body.get_dates()
    try:
        stats = await fetch_index_stats(
            index=body.index,
            geometry=body.geometry,
            date_from=date_from,
            date_to=date_to,
            client=client,
        )
    except httpx.HTTPStatusError as e:
        detail = f"Sentinel Hub error: {e.response.status_code}"
        try:
            detail += f" - {e.response.json().get('message', '')}"
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=detail)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Statistics calculation failed: {str(e)}")

    meta = INDEX_METADATA[body.index]
    interpretation = _interpret_value(body.index, stats["mean"], meta)

    return {
        "index": body.index,
        "full_name": meta["full_name"],
        "statistics": stats,
        "interpretation": interpretation,
        "date_from": date_from,
        "date_to": date_to,
    }


def _extract_coords(geometry: dict) -> list:
    geo_type = geometry.get("type", "")
    if geo_type == "Polygon":
        return geometry["coordinates"][0]
    elif geo_type == "MultiPolygon":
        coords = []
        for poly in geometry["coordinates"]:
            coords.extend(poly[0])
        return coords
    elif geo_type == "Point":
        return [geometry["coordinates"]]
    return []


def _interpret_value(index: str, mean: float, meta: dict) -> str:
    good_min, good_max = meta.get("good_range", (0.3, 0.8))
    descriptions = {
        "NDVI": {
            "low": "Sparse or stressed vegetation / bare soil",
            "good": "Healthy and dense vegetation",
            "high": "Very dense lush vegetation",
        },
        "NDMI": {
            "low": "Dry / water-stressed vegetation",
            "good": "Well-watered vegetation",
            "high": "Very high water content",
        },
        "EVI": {
            "low": "Low vegetation cover",
            "good": "Healthy vegetation",
            "high": "Very dense canopy",
        },
        "MNDWI": {
            "low": "Dry land / soil dominant",
            "good": "Moderate soil moisture",
            "high": "Water body detected",
        },
        "SAVI": {
            "low": "Sparse vegetation on bright soil",
            "good": "Moderate vegetation density",
            "high": "Dense vegetation",
        },
        "GNDVI": {
            "low": "Low chlorophyll content",
            "good": "Moderate chlorophyll, healthy crop",
            "high": "High chlorophyll, dense canopy",
        },
        "GCI": {
            "low": "Low chlorophyll / stressed crop",
            "good": "Normal chlorophyll level",
            "high": "Very high chlorophyll",
        },
        "SIPI": {
            "low": "High carotenoid/chlorophyll ratio (stressed)",
            "good": "Balanced pigment ratio",
            "high": "Possible nutrient stress or senescence",
        },
        "NBR": {
            "low": "Burned or severely stressed area",
            "good": "Healthy unburned vegetation",
            "high": "Dense green healthy vegetation",
        },
        "MGRVI": {
            "low": "Low vegetation / soil dominant",
            "good": "Moderate vegetation cover",
            "high": "Dense green cover",
        },
        "NDWI": {
            "low": "Dry vegetation, water deficit",
            "good": "Normal water content",
            "high": "Saturated / flooded",
        },
    }
    labels = descriptions.get(index, {"low": "Below normal", "good": "Normal", "high": "Above normal"})
    if mean < good_min:
        return labels["low"]
    elif mean > good_max:
        return labels["high"]
    else:
        return labels["good"]
