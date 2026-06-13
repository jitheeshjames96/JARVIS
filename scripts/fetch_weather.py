#!/usr/bin/env python3
"""Fetch live weather for dashboard HUD (Open-Meteo, no API key)."""

from __future__ import annotations

import json
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "cache" / "weather.json"
IST = ZoneInfo("Asia/Kolkata")

# Kochi, Kerala (Asia/Kolkata)
LAT, LON = 9.9312, 76.2673
LOCATION = "Kochi, India"


def fetch() -> dict:
    url = (
        "https://api.open-meteo.com/v1/forecast?"
        f"latitude={LAT}&longitude={LON}"
        "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
        "&daily=temperature_2m_max,temperature_2m_min,weather_code"
        "&timezone=Asia%2FKolkata&forecast_days=7"
    )
    try:
        with urllib.request.urlopen(url, timeout=12) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        return {"error": str(exc), "location": LOCATION}

    current = data.get("current", {})
    daily = data.get("daily", {})
    forecast = []
    times = daily.get("time", [])
    for i, day in enumerate(times[:7]):
        forecast.append({
            "date": day,
            "day_label": datetime.strptime(day, "%Y-%m-%d").strftime("%a"),
            "max_c": daily.get("temperature_2m_max", [None] * 7)[i],
            "min_c": daily.get("temperature_2m_min", [None] * 7)[i],
            "code": daily.get("weather_code", [0] * 7)[i],
        })

    return {
        "location": LOCATION,
        "fetched_at": datetime.now(IST).isoformat(),
        "current": {
            "temp_c": current.get("temperature_2m"),
            "humidity": current.get("relative_humidity_2m"),
            "wind_kmh": current.get("wind_speed_10m"),
            "code": current.get("weather_code", 0),
            "description": _wmo_label(current.get("weather_code", 0)),
        },
        "forecast": forecast,
    }


def _wmo_label(code: int) -> str:
    labels = {
        0: "Clear", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 51: "Drizzle", 61: "Rain", 63: "Rain", 65: "Heavy rain",
        71: "Snow", 80: "Showers", 95: "Thunderstorm",
    }
    return labels.get(code, "Variable")


def main():
    payload = fetch()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
        f.write("\n")
    print(f"Weather written: {OUT}")


if __name__ == "__main__":
    main()
