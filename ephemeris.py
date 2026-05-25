"""
ephemeris.py — VedAstro API client with per-date in-memory cache.

VedAstro REST API (free, no auth):
  GET https://api.vedastro.org/api/Calculate/PlanetZodiacSign
      /PlanetName/{planet}
      /Location/{lat},{lon}
      /Time/{HH:MM}/{DD}/{MM}/{YYYY}/{tz_offset}

Response:
  {"Status": "Pass", "Payload": {"PlanetZodiacSign": {"ZodiacName": "Gemini", "DegreesInSign": 4.23}}}
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Tuple

import httpx

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

VEDASTRO_BASE = "https://api.vedastro.org/api/Calculate"
PLANETS       = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
TIMEOUT_SEC   = 15.0
MAX_RETRIES   = 2

# In-memory cache keyed by (date_str, lat, lon) — planets don't move much intra-day
_cache: Dict[str, Dict] = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _tz_from_lon(lon: float) -> str:
    """Approximate UTC offset from longitude (±HH:00). Good enough for transits."""
    offset = round(lon / 15)
    sign   = "+" if offset >= 0 else "-"
    return f"{sign}{abs(offset):02d}:00"


def _build_url(planet: str, date_str: str, lat: float, lon: float) -> str:
    d  = datetime.strptime(date_str, "%Y-%m-%d")
    tz = _tz_from_lon(lon)
    dd, mm, yyyy = f"{d.day:02d}", f"{d.month:02d}", str(d.year)
    # Use noon local time — planetary positions don't shift sign mid-day for transits
    return (
        f"{VEDASTRO_BASE}/PlanetZodiacSign"
        f"/PlanetName/{planet}"
        f"/Location/{lat},{lon}"
        f"/Time/12:00/{dd}/{mm}/{yyyy}/{tz}"
    )


def _parse_response(planet: str, data: dict) -> Dict:
    """Extract sign + degree from VedAstro response payload."""
    if data.get("Status") != "Pass":
        raise ValueError(f"VedAstro non-pass status for {planet}: {data.get('Status')}")

    payload = data.get("Payload", {}).get("PlanetZodiacSign", {})

    # VedAstro sometimes wraps in a list when fetching "All"
    if isinstance(payload, list):
        payload = payload[0] if payload else {}

    sign   = payload.get("ZodiacName") or payload.get("Sign")
    degree = payload.get("DegreesInSign") or payload.get("Degree") or 0.0

    if not sign:
        raise ValueError(f"Missing ZodiacName in VedAstro response for {planet}: {payload}")

    return {"sign": sign, "degree": round(float(degree), 2)}


# ── Core fetch (single planet, with retry) ────────────────────────────────────

async def _fetch_one(client: httpx.AsyncClient, planet: str, date_str: str, lat: float, lon: float) -> Tuple[str, Dict]:
    url = _build_url(planet, date_str, lat, lon)
    last_err = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.debug(f"[{planet}] attempt {attempt} → {url}")
            resp = await client.get(url, timeout=TIMEOUT_SEC)
            resp.raise_for_status()
            data = resp.json()
            return planet.lower(), _parse_response(planet, data)

        except httpx.TimeoutException:
            last_err = f"timeout after {TIMEOUT_SEC}s"
            logger.warning(f"[{planet}] attempt {attempt} timed out")
        except httpx.HTTPStatusError as e:
            last_err = f"HTTP {e.response.status_code}"
            logger.warning(f"[{planet}] attempt {attempt} HTTP error: {last_err}")
            break   # don't retry 4xx
        except Exception as e:
            last_err = str(e)
            logger.warning(f"[{planet}] attempt {attempt} error: {last_err}")

        if attempt < MAX_RETRIES:
            await asyncio.sleep(0.5)

    raise RuntimeError(f"VedAstro failed for {planet} after {MAX_RETRIES} attempts: {last_err}")


# ── Public API ────────────────────────────────────────────────────────────────

async def get_planet_positions(date_str: str, lat: float, lon: float) -> Dict:
    """
    Return {planet_lower: {sign, degree}} for all 9 Vedic planets.
    Results are cached by (date, lat, lon) — one API call per unique date.
    """
    cache_key = f"{date_str}|{lat}|{lon}"
    if cache_key in _cache:
        logger.info(f"Cache hit: {cache_key}")
        return _cache[cache_key]

    logger.info(f"Fetching all planets from VedAstro: date={date_str} lat={lat} lon={lon}")

    async with httpx.AsyncClient() as client:
        tasks   = [_fetch_one(client, p, date_str, lat, lon) for p in PLANETS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    positions = {}
    errors    = []
    for item in results:
        if isinstance(item, Exception):
            errors.append(str(item))
        else:
            planet_key, planet_data = item
            positions[planet_key] = planet_data

    if errors:
        logger.error(f"VedAstro errors: {errors}")
        raise RuntimeError("; ".join(errors))

    _cache[cache_key] = positions
    logger.info(f"Cached {len(positions)} planets for {cache_key}")
    return positions
