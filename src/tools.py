from __future__ import annotations

import httpx

from src.config import settings


async def lookup_destination(name: str) -> dict:
    """Resolve destination coordinates using OpenStreetMap Nominatim."""
    headers = {"User-Agent": "travel-planner-agent/0.1 (course project)"}
    params = {"q": name, "format": "jsonv2", "limit": 1, "accept-language": "zh-CN"}
    async with httpx.AsyncClient(timeout=settings.request_timeout, headers=headers) as client:
        response = await client.get("https://nominatim.openstreetmap.org/search", params=params)
        response.raise_for_status()
        rows = response.json()
    if not rows:
        return {}
    row = rows[0]
    return {"name": row["display_name"], "lat": float(row["lat"]), "lon": float(row["lon"])}


async def lookup_weather(lat: float, lon: float) -> dict:
    """Fetch a short forecast from Open-Meteo (no API key required)."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "timezone": "auto",
        "forecast_days": 7,
    }
    async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
        response = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
        response.raise_for_status()
        return response.json().get("daily", {})


async def enrich_destination(destination: str) -> tuple[dict, list[str]]:
    sources: list[str] = []
    try:
        place = await lookup_destination(destination)
        if not place:
            return {}, sources
        sources.append("OpenStreetMap Nominatim")
        weather = await lookup_weather(place["lat"], place["lon"])
        if weather:
            sources.append("Open-Meteo")
        return {"place": place, "weather": weather}, sources
    except (httpx.HTTPError, ValueError, KeyError):
        return {}, sources

