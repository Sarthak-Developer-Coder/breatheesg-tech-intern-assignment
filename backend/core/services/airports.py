from __future__ import annotations

import json
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Airport:
    iata: str
    lat: float
    lon: float
    name: str = ''
    city: str = ''
    country: str = ''


@lru_cache(maxsize=1)
def _load_airports() -> dict[str, Airport]:
    path = Path(__file__).resolve().parent.parent / 'reference' / 'airports_min.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    out: dict[str, Airport] = {}
    for row in data:
        iata = str(row.get('iata', '')).upper().strip()
        if not iata:
            continue
        out[iata] = Airport(
            iata=iata,
            lat=float(row['lat']),
            lon=float(row['lon']),
            name=str(row.get('name', '')),
            city=str(row.get('city', '')),
            country=str(row.get('country', '')),
        )
    return out


def get_airport(iata: str) -> Airport | None:
    if not iata:
        return None
    return _load_airports().get(iata.upper().strip())


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Radius of Earth in km
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


def estimate_flight_distance_km(origin_iata: str, destination_iata: str) -> float | None:
    origin = get_airport(origin_iata)
    dest = get_airport(destination_iata)
    if origin is None or dest is None:
        return None

    if origin.iata == dest.iata:
        return 0.0

    return haversine_km(origin.lat, origin.lon, dest.lat, dest.lon)
