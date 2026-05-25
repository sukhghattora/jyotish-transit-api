"""
main.py — Jyotish Transit API v2
Powered by VedAstro (free, no auth required).

Flow:
  1. Validate query params (date format, lat/lon range, lagna sign)
  2. Call ephemeris.get_planet_positions() → hits VedAstro API (or cache)
  3. Call houses.calculate_houses() → Equal House placement
  4. Return structured JSON response
"""

import os
import uuid
import logging
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from ephemeris import get_planet_positions
from houses import SIGNS, calculate_houses

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Jyotish Transit API",
    version="2.0.0",
    description="Real-time Vedic astrology transits via VedAstro. No API key needed.",
)

VALID_SIGNS = set(SIGNS)


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["meta"])
async def health():
    return {"status": "ok", "service": "jyotish-transit-api", "version": "2.0.0"}


# ── Transits ──────────────────────────────────────────────────────────────────
@app.get("/transits", tags=["transits"])
async def get_transits(
    client_id: str = Query(...,  description="Client identifier (any string)"),
    date:      str = Query(...,  description="Date in YYYY-MM-DD format"),
    lat:       float = Query(..., ge=-90,   le=90,   description="Birth latitude"),
    lon:       float = Query(..., ge=-180,  le=180,  description="Birth longitude"),
    lagna:     str = Query(...,  description="Lagna sign + degree, e.g. 'Sagittarius 12.5'"),
):
    """
    Return current planetary transits with house placement for a given Lagna.

    Example:
        GET /transits?client_id=sukhdeep&date=2026-05-25&lat=28.7041&lon=77.1025&lagna=Sagittarius%2012.5
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"[{request_id}] client={client_id} date={date} lat={lat} lon={lon} lagna={lagna!r}")

    # ── 1. Validate date ──────────────────────────────────────────────────────
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid date '{date}'. Use YYYY-MM-DD.", "request_id": request_id},
        )

    # ── 2. Parse + validate lagna ─────────────────────────────────────────────
    parts = lagna.strip().split(maxsplit=1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid lagna '{lagna}'. Use e.g. 'Sagittarius 12.5'", "request_id": request_id},
        )

    lagna_sign = parts[0].strip().capitalize()
    if lagna_sign not in VALID_SIGNS:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid lagna sign '{lagna_sign}'. Valid: {', '.join(sorted(VALID_SIGNS))}", "request_id": request_id},
        )

    try:
        lagna_degree = float(parts[1])
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail={"error": f"Invalid lagna degree '{parts[1]}'. Must be a number.", "request_id": request_id},
        )

    if not (0 <= lagna_degree < 30):
        raise HTTPException(
            status_code=400,
            detail={"error": f"Lagna degree {lagna_degree} out of range. Must be 0–29.99.", "request_id": request_id},
        )

    # ── 3. Fetch planets from VedAstro ────────────────────────────────────────
    try:
        positions = await get_planet_positions(date, lat, lon)
    except RuntimeError as e:
        logger.error(f"[{request_id}] VedAstro error: {e}")
        raise HTTPException(
            status_code=503,
            detail={"error": "VedAstro API unavailable. Try again shortly.", "detail": str(e), "request_id": request_id},
        )
    except Exception as e:
        logger.exception(f"[{request_id}] Unexpected error fetching planets")
        raise HTTPException(
            status_code=500,
            detail={"error": "Internal server error.", "request_id": request_id},
        )

    # ── 4. Calculate houses ───────────────────────────────────────────────────
    try:
        transits = calculate_houses(positions, lagna_sign, lagna_degree)
    except Exception as e:
        logger.exception(f"[{request_id}] House calculation error")
        raise HTTPException(status_code=500, detail={"error": str(e), "request_id": request_id})

    logger.info(f"[{request_id}] OK — {len(transits)} planets returned")

    return {
        "client_id":  client_id,
        "date":       date,
        "lagna":      {"sign": lagna_sign, "degree": lagna_degree},
        "transits":   transits,
        "timestamp":  datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "request_id": request_id,
    }


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting Jyotish Transit API on port {port}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, log_level="info")
