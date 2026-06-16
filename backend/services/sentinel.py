import asyncio
import base64
import time
from datetime import datetime, timedelta
import httpx
from config import (
    SENTINEL_HUB_AUTH_URL,
    SENTINEL_HUB_PROCESS_URL,
    SENTINEL_HUB_STATS_URL,
    SENTINEL_HUB_CLIENT_ID,
    SENTINEL_HUB_CLIENT_SECRET,
    INDEX_EVALSCRIPTS_VISUAL,
    INDEX_EVALSCRIPTS_STATS,
)

_token_cache: dict = {"access_token": None, "expires_at": 0}
_token_lock = asyncio.Lock()


async def get_access_token(client: httpx.AsyncClient) -> str:
    async with _token_lock:
        if _token_cache["access_token"] and time.time() < _token_cache["expires_at"] - 60:
            return _token_cache["access_token"]

        resp = await client.post(
            SENTINEL_HUB_AUTH_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": SENTINEL_HUB_CLIENT_ID,
                "client_secret": SENTINEL_HUB_CLIENT_SECRET,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        _token_cache["access_token"] = data["access_token"]
        _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
        return _token_cache["access_token"]


def _build_time_range(date_from: str, date_to: str) -> dict:
    return {
        "from": f"{date_from}T00:00:00Z",
        "to": f"{date_to}T23:59:59Z",
    }


def _build_input_block(geometry: dict, date_from: str, date_to: str) -> dict:
    return {
        "bounds": {
            "geometry": geometry,
            "properties": {"crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84"},
        },
        "data": [
            {
                "dataFilter": {
                    "timeRange": _build_time_range(date_from, date_to),
                    "mosaickingOrder": "leastCC",
                },
                "type": "sentinel-2-l2a",
            }
        ],
    }


async def fetch_index_map(
    index: str,
    geometry: dict,
    date_from: str,
    date_to: str,
    client: httpx.AsyncClient,
) -> str:
    """Call Sentinel Hub Process API and return base64-encoded PNG."""
    token = await get_access_token(client)
    evalscript = INDEX_EVALSCRIPTS_VISUAL.get(index)
    if not evalscript:
        raise ValueError(f"Unknown index: {index}")

    payload = {
        "input": _build_input_block(geometry, date_from, date_to),
        "output": {
            "width": 512,
            "height": 512,
            "responses": [
                {"identifier": "default", "format": {"type": "image/png"}}
            ],
        },
        "evalscript": evalscript,
    }

    resp = await client.post(
        SENTINEL_HUB_PROCESS_URL,
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=60.0,
    )
    resp.raise_for_status()

    png_bytes = resp.content
    b64 = base64.b64encode(png_bytes).decode("utf-8")
    return f"data:image/png;base64,{b64}"


async def fetch_index_stats(
    index: str,
    geometry: dict,
    date_from: str,
    date_to: str,
    client: httpx.AsyncClient,
) -> dict:
    """Call Sentinel Hub Statistical API and return parsed statistics."""
    token = await get_access_token(client)
    evalscript = INDEX_EVALSCRIPTS_STATS.get(index)
    if not evalscript:
        raise ValueError(f"Unknown index: {index}")

    index_key = index.lower()

    payload = {
        "input": _build_input_block(geometry, date_from, date_to),
        "aggregation": {
            "timeRange": _build_time_range(date_from, date_to),
            "aggregationInterval": {"of": "P30D"},
            "resx": 10,
            "resy": 10,
            "evalscript": evalscript,
        },
        "calculations": {
            index_key: {
                "histograms": {
                    "default": {"nBins": 20, "lowEdge": -1.5, "highEdge": 1.5}
                },
                "statistics": {
                    "default": {
                        "percentiles": {"k": [10, 25, 50, 75, 90]}
                    }
                },
            }
        },
    }

    resp = await client.post(
        SENTINEL_HUB_STATS_URL,
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=60.0,
    )
    resp.raise_for_status()

    raw = resp.json()
    data = raw.get("data", [])
    if not data:
        raise ValueError("No satellite data available for the selected date range. Try extending the date range.")

    # Attempt to extract stats from any output key
    outputs = data[0].get("outputs", {})
    stats = None

    for out_key, out_val in outputs.items():
        bands = out_val.get("bands", {})
        for band_key, band_val in bands.items():
            stats = band_val.get("stats")
            if stats:
                break
        if stats:
            break

    if not stats:
        raise ValueError("Could not parse statistics from Sentinel Hub response.")

    percentiles = stats.get("percentiles", {})

    return {
        "mean": round(stats.get("mean", 0), 4),
        "min": round(stats.get("min", 0), 4),
        "max": round(stats.get("max", 0), 4),
        "stDev": round(stats.get("stDev", 0), 4),
        "percentiles": {
            "p10": round(percentiles.get("10.0", percentiles.get("10", 0)), 4),
            "p25": round(percentiles.get("25.0", percentiles.get("25", 0)), 4),
            "p50": round(percentiles.get("50.0", percentiles.get("50", 0)), 4),
            "p75": round(percentiles.get("75.0", percentiles.get("75", 0)), 4),
            "p90": round(percentiles.get("90.0", percentiles.get("90", 0)), 4),
        },
        "noDataPixels": stats.get("noDataCount", 0),
        "totalPixels": stats.get("sampleCount", 0),
    }


def get_default_date_range() -> tuple[str, str]:
    today = datetime.utcnow()
    date_to = today.strftime("%Y-%m-%d")
    date_from = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    return date_from, date_to
