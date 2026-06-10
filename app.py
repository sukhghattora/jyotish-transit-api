from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path
import swisseph as swe

app = FastAPI(title="Jyotish Transit API", version="1.0.0")

# ── Planet map ────────────────────────────────────────────────────────────────
PLANETS = {
    "Sun":     swe.SUN,
    "Moon":    swe.MOON,
    "Mercury": swe.MERCURY,
    "Venus":   swe.VENUS,
    "Mars":    swe.MARS,
    "Jupiter": swe.JUPITER,
    "Saturn":  swe.SATURN,
    "Rahu":    swe.MEAN_NODE,   # True North Node
    "Ketu":    None,            # Derived: Rahu + 180°
    "Uranus":  swe.URANUS,
    "Neptune": swe.NEPTUNE,
}

RASHIS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishtha", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

ASPECT_ANGLES = [
    (0,   "Conjunction",  8),
    (60,  "Sextile",      5),
    (90,  "Square",       6),
    (120, "Trine",        6),
    (180, "Opposition",   8),
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def to_jd(year, month, day, hour, minute, second, tz_offset):
    """Local time → Julian Day (UT)."""
    ut = hour + minute / 60.0 + second / 3600.0 - tz_offset
    return swe.julday(year, month, day, ut)


def planet_lon(jd, planet_id):
    flags = swe.FLG_SWIEPH | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd, planet_id, flags)
    return result[0]   # tropical longitude


def sidereal_lon(tropical_lon, jd):
    """Tropical → Sidereal using Lahiri ayanamsha."""
    ayan = swe.get_ayanamsa_ut(jd)
    return (tropical_lon - ayan) % 360


def enrich(lon_sid):
    rashi_idx     = int(lon_sid / 30)
    rashi_deg     = lon_sid % 30
    nak_idx       = int(lon_sid / (360 / 27))
    nak_pada      = int((lon_sid % (360 / 27)) / (360 / 108)) + 1
    return {
        "sidereal_longitude": round(lon_sid, 4),
        "rashi":              RASHIS[rashi_idx],
        "rashi_degrees":      round(rashi_deg, 2),
        "nakshatra":          NAKSHATRAS[nak_idx],
        "nakshatra_pada":     nak_pada,
    }


def calc_aspects(transit_positions, natal_positions):
    aspects = []
    for t_name, t_data in transit_positions.items():
        for n_name, n_data in natal_positions.items():
            diff = abs(t_data["sidereal_longitude"] - n_data["sidereal_longitude"]) % 360
            if diff > 180:
                diff = 360 - diff
            for angle, label, orb in ASPECT_ANGLES:
                if abs(diff - angle) <= orb:
                    aspects.append({
                        "transit_planet": t_name,
                        "natal_planet":   n_name,
                        "aspect":         label,
                        "orb_deg":        round(abs(diff - angle), 2),
                        "transit_rashi":  t_data["rashi"],
                        "natal_rashi":    n_data["rashi"],
                    })
    return aspects


def get_positions(jd):
    """Return sidereal positions for all planets at given JD."""
    positions = {}
    rahu_sid = None
    for name, pid in PLANETS.items():
        if pid is None:          # Ketu
            if rahu_sid is not None:
                ketu_sid = (rahu_sid + 180) % 360
                positions["Ketu"] = enrich(ketu_sid)
            continue
        lon_trop = planet_lon(jd, pid)
        lon_sid  = sidereal_lon(lon_trop, jd)
        positions[name] = enrich(lon_sid)
        if name == "Rahu":
            rahu_sid = lon_sid
    return positions

# ── Schema ────────────────────────────────────────────────────────────────────

class TransitRequest(BaseModel):
    birth_date: str   # YYYY-MM-DD
    birth_time: str   # HH:MM or HH:MM:SS
    birth_lat:  float
    birth_lon:  float
    birth_tz:   float  # e.g. 5.5 for IST

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "jyotish-transit-api"}


@app.get("/prompt")
def get_prompt():
    prompt_path = Path(__file__).parent / "system_prompt.txt"
    return {"system_prompt": prompt_path.read_text()}


def _compute_transits(req: TransitRequest):
    swe.set_sid_mode(swe.SIDM_LAHIRI)

    bd = datetime.strptime(req.birth_date, "%Y-%m-%d")
    time_parts = req.birth_time.split(":")
    bh = int(time_parts[0])
    bm = int(time_parts[1])
    bs = int(time_parts[2]) if len(time_parts) > 2 else 0

    birth_jd   = to_jd(bd.year, bd.month, bd.day, bh, bm, bs, req.birth_tz)
    natal_pos  = get_positions(birth_jd)

    now = datetime.utcnow()
    transit_jd  = swe.julday(now.year, now.month, now.day,
                              now.hour + now.minute / 60.0 + now.second / 3600.0)
    transit_pos = get_positions(transit_jd)
    aspects     = calc_aspects(transit_pos, natal_pos)

    return {
        "transit_date":      now.strftime("%Y-%m-%d"),
        "transit_time_utc":  now.strftime("%H:%M"),
        "natal_positions":   natal_pos,
        "transit_positions": transit_pos,
        "transit_aspects":   aspects,
    }


def _format_positions(label: str, positions: dict) -> str:
    lines = [f"{label}:"]
    for planet, data in positions.items():
        lines.append(
            f"  {planet}: {data['rashi']} {data['rashi_degrees']:.2f}° "
            f"({data['nakshatra']} pada {data['nakshatra_pada']})"
        )
    return "\n".join(lines)


def _build_context_block(data: dict) -> str:
    transit_planets = _format_positions("Today's transit positions", data["transit_positions"])
    natal_planets   = _format_positions("Natal positions", data["natal_positions"])

    aspect_lines = []
    for a in data["transit_aspects"]:
        aspect_lines.append(
            f"  Transit {a['transit_planet']} ({a['transit_rashi']}) "
            f"{a['aspect']} natal {a['natal_planet']} ({a['natal_rashi']}) "
            f"— orb {a['orb_deg']}°"
        )
    aspects_block = "Active aspects:\n" + ("\n".join(aspect_lines) if aspect_lines else "  None within orb")

    return (
        f"=== LIVE JYOTISH TRANSIT DATA ({data['transit_date']} {data['transit_time_utc']} UTC) ===\n\n"
        f"{transit_planets}\n\n"
        f"{natal_planets}\n\n"
        f"{aspects_block}"
    )


@app.post("/transits")
def get_transits(req: TransitRequest):
    try:
        return _compute_transits(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transits/context")
def get_transits_context(req: TransitRequest):
    """Returns a pre-formatted plain-text block ready to paste into an n8n AI node message."""
    try:
        data = _compute_transits(req)
        return {"context": _build_context_block(data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
