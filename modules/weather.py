"""
modules/weather.py
==================

Geocoding (ZIP -> lat/lon) and forecast retrieval.

Design goals:
  * Prefer free / no-key APIs (Zippopotam.us for ZIP, Open-Meteo for weather).
  * Keep the provider behind small functions so another API can be swapped in
    by editing config + one function here.
  * Return plain Python dicts/lists so the rest of the app stays decoupled
    from any specific API's JSON shape.

No API keys are required for the defaults. If a future provider needs one,
read it from Streamlit secrets / env via `_api_key()` - never hard-code it.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional

from . import config


# ---------------------------------------------------------------------------
# Low-level HTTP
# ---------------------------------------------------------------------------
class WeatherError(Exception):
    """Raised for any geocoding / forecast retrieval failure."""


def _http_get_json(url: str, params: Optional[Dict] = None) -> dict:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "SnowseedSnowmaking/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8")
        return json.loads(raw)
    except urllib.error.HTTPError as exc:  # type: ignore[attr-defined]
        raise WeatherError(f"Service returned HTTP {exc.code} for {url}") from exc
    except Exception as exc:  # noqa: BLE001
        raise WeatherError(f"Network/parse error contacting {url}: {exc}") from exc


def _api_key() -> Optional[str]:
    """Optional API key from env (or Streamlit secrets, set into env upstream)."""
    return os.environ.get(config.WEATHER_API_KEY_ENV)


# ---------------------------------------------------------------------------
# Geocoding: ZIP -> lat/lon
# ---------------------------------------------------------------------------
@dataclass
class Location:
    zip_code: str
    latitude: float
    longitude: float
    place_name: str
    state: str


def geocode_zip(zip_code: str) -> Location:
    """
    Convert a US ZIP code to a Location via Zippopotam.us (free, no key).

    Swap providers by editing config.GEOCODE_PROVIDER and this function.
    """
    zip_code = (zip_code or "").strip()
    if config.GEOCODE_PROVIDER == "zippopotam":
        url = config.ZIPPOPOTAM_URL.format(zip=urllib.parse.quote(zip_code))
        data = _http_get_json(url)
        try:
            place = data["places"][0]
            return Location(
                zip_code=zip_code,
                latitude=float(place["latitude"]),
                longitude=float(place["longitude"]),
                place_name=place.get("place name", ""),
                state=place.get("state abbreviation", place.get("state", "")),
            )
        except (KeyError, IndexError, ValueError) as exc:
            raise WeatherError(
                f"Could not find location for ZIP '{zip_code}'."
            ) from exc
    raise WeatherError(f"Unknown geocode provider: {config.GEOCODE_PROVIDER}")


# ---------------------------------------------------------------------------
# Forecast retrieval
# ---------------------------------------------------------------------------
@dataclass
class HourlyPoint:
    time_iso: str          # local ISO timestamp, e.g. "2026-01-12T23:00"
    temp_f: float
    humidity_pct: Optional[float]
    dewpoint_f: Optional[float]
    wind_mph: Optional[float]


@dataclass
class Forecast:
    location: Location
    timezone: str
    hourly: List[HourlyPoint]


def get_forecast(location: Location, days: int = config.FORECAST_DAYS) -> Forecast:
    """
    Fetch hourly forecast for a Location using Open-Meteo (free, no key).

    Pulls temperature, relative humidity, dew point, and wind speed in
    Fahrenheit / mph with local timezone. Structured so a 14-day request is a
    one-line change once you confirm the provider returns it.
    """
    days = max(1, min(days, config.FORECAST_DAYS_MAX))

    if config.WEATHER_PROVIDER == "open-meteo":
        params = {
            "latitude": location.latitude,
            "longitude": location.longitude,
            "hourly": "temperature_2m,relative_humidity_2m,dew_point_2m,wind_speed_10m",
            "temperature_unit": "fahrenheit",
            "wind_speed_unit": "mph",
            "timezone": "auto",
            "forecast_days": days,
        }
        data = _http_get_json(config.OPEN_METEO_URL, params)
        return _parse_open_meteo(location, data)

    raise WeatherError(f"Unknown weather provider: {config.WEATHER_PROVIDER}")


def _parse_open_meteo(location: Location, data: dict) -> Forecast:
    hourly = data.get("hourly", {})
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    hums = hourly.get("relative_humidity_2m", [])
    dews = hourly.get("dew_point_2m", [])
    winds = hourly.get("wind_speed_10m", [])

    if not times or not temps:
        raise WeatherError("Forecast response did not contain hourly data.")

    def _at(seq: List, i: int):
        return seq[i] if i < len(seq) and seq[i] is not None else None

    points: List[HourlyPoint] = []
    for i, t in enumerate(times):
        temp = _at(temps, i)
        if temp is None:
            continue
        points.append(
            HourlyPoint(
                time_iso=t,
                temp_f=float(temp),
                humidity_pct=(None if _at(hums, i) is None else float(hums[i])),
                dewpoint_f=(None if _at(dews, i) is None else float(dews[i])),
                wind_mph=(None if _at(winds, i) is None else float(winds[i])),
            )
        )

    return Forecast(
        location=location,
        timezone=data.get("timezone", "local"),
        hourly=points,
    )


# ---------------------------------------------------------------------------
# Convenience: ZIP straight to forecast
# ---------------------------------------------------------------------------
def forecast_for_zip(zip_code: str, days: int = config.FORECAST_DAYS) -> Forecast:
    return get_forecast(geocode_zip(zip_code), days=days)
