"""
panchang_calculator.py
Vedic Panchanga calculations using Swiss Ephemeris with KP (Krishnamurti) Ayanamsha.

Exported functions:
    calculate_panchanga(lat, lon, date_str=None, tz_str='UTC') -> dict
    calculate_sunrise_sunset(lat, lon, date_str=None, tz_str='UTC') -> dict
    get_moon_phase(date_str=None, tz_str='UTC') -> dict
    get_hora_chart(date_str=None, tz_str='UTC') -> dict

Ayanamsha: KP Krishnamurti (swe.SIDM_KRISHNAMURTI = 5)
House system: Whole Sign (Equal from Lagna)
"""

import swisseph as swe
import pytz
from datetime import datetime, date, timedelta
from typing import Optional

# ── Ayanamsha: KP Krishnamurti ─────────────────────────────────────────────────
swe.set_sid_mode(swe.SIDM_KRISHNAMURTI)   # constant = 5
EPHE_PATH = "/opt/ephemeris"
swe.set_ephe_path(EPHE_PATH)

# ── Lookup tables ──────────────────────────────────────────────────────────────
SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

SIGN_LORDS = {
    1: "Mars", 2: "Venus", 3: "Mercury", 4: "Moon",   5: "Sun",    6: "Mercury",
    7: "Venus", 8: "Mars",  9: "Jupiter", 10: "Saturn", 11: "Saturn", 12: "Jupiter"
}

NAKSHATRAS = [
    "Ashwini",         "Bharani",         "Krittika",
    "Rohini",          "Mrigashira",      "Ardra",
    "Punarvasu",       "Pushya",          "Ashlesha",
    "Magha",           "Purva Phalguni",  "Uttara Phalguni",
    "Hasta",           "Chitra",          "Swati",
    "Vishakha",        "Anuradha",        "Jyeshtha",
    "Mula",            "Purva Ashadha",   "Uttara Ashadha",
    "Shravana",        "Dhanishtha",      "Shatabhisha",
    "Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

NAKSHATRA_LORDS = [
    "Ketu","Venus","Sun","Moon","Mars","Rahu",
    "Jupiter","Saturn","Mercury","Ketu","Venus","Sun",
    "Moon","Mars","Rahu","Jupiter","Saturn","Mercury",
    "Ketu","Venus","Sun","Moon","Mars","Rahu",
    "Jupiter","Saturn","Mercury"
]

# KP sub-lord sequence (120-year Vimshottari) and durations in years
DASHA_SEQUENCE = ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]
DASHA_YEARS    = {"Ketu":7,"Venus":20,"Sun":6,"Moon":10,"Mars":7,"Rahu":18,"Jupiter":16,"Saturn":19,"Mercury":17}

TITHIS = [
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dvadashi","Trayodashi","Chaturdashi","Purnima",
    "Pratipada","Dvitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dvadashi","Trayodashi","Chaturdashi","Amavasya"
]

YOGAS = [
    "Vishkambha","Priti","Ayushman","Saubhagya","Shobhana",
    "Atiganda","Sukarma","Dhriti","Shula","Ganda",
    "Vriddhi","Dhruva","Vyaghata","Harshana","Vajra",
    "Siddhi","Vyatipata","Variyana","Parigha","Shiva",
    "Siddha","Sadhya","Shubha","Shukla","Brahma",
    "Indra","Vaidhriti"
]

KARANAS = [
    "Kimstughna",                                               # index 0: fixed
    "Bava","Balava","Kaulava","Taitila","Garaja","Vanija","Vishti",  # 1-7: movable
    "Shakuni","Chatushpada","Naga"                              # 8-10: fixed end
]

VARAS      = ["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"]
VARA_LORDS = {
    "Sunday":"Sun","Monday":"Moon","Tuesday":"Mars",
    "Wednesday":"Mercury","Thursday":"Jupiter","Friday":"Venus","Saturday":"Saturn"
}

# Hora lords in order (day and night, alternating Sun/Moon chains)
HORA_LORDS_DAY   = ["Sun","Venus","Mercury","Moon","Saturn","Jupiter","Mars"]
HORA_LORDS_NIGHT = ["Jupiter","Mars","Sun","Venus","Mercury","Moon","Saturn"]

INAUSPICIOUS_TITHIS  = {"Chaturthi","Ashtami","Chaturdashi","Amavasya"}
INAUSPICIOUS_YOGAS   = {"Vishkambha","Atiganda","Shula","Ganda","Vyaghata",
                         "Vyatipata","Parigha","Vaidhriti"}
INAUSPICIOUS_KARANAS = {"Vishti"}

# Rahu Kala by weekday (slot 1-8, each ~90 min in a 12-hr day)
RAHU_KALA_SLOT = {0:8,1:2,2:7,3:5,4:6,5:4,6:3}  # Sun=0 … Sat=6
GULIKA_SLOT    = {0:6,1:5,2:4,3:3,4:2,5:1,6:7}
YAMAGANDA_SLOT = {0:4,1:3,2:2,3:1,4:7,5:6,6:5}


# ── Internal helpers ───────────────────────────────────────────────────────────

def _parse_tz(tz_str: str) -> pytz.BaseTzInfo:
    try:
        return pytz.timezone(tz_str)
    except Exception:
        return pytz.UTC


def _to_jd(dt: datetime) -> float:
    """UTC datetime → Julian Day Number."""
    return swe.julday(dt.year, dt.month, dt.day,
                      dt.hour + dt.minute / 60.0 + dt.second / 3600.0)


def _resolve_datetime(date_str: Optional[str], tz_str: str, hour: int = 0) -> tuple:
    """Return (dt_local, dt_utc, jd) for a given date string and timezone."""
    tz_obj = _parse_tz(tz_str)
    if date_str:
        try:
            d = date.fromisoformat(date_str)
        except ValueError:
            raise ValueError(f"date must be YYYY-MM-DD, got: {date_str!r}")
        dt_local = tz_obj.localize(datetime(d.year, d.month, d.day, hour, 0, 0))
    else:
        now = datetime.now(tz_obj)
        dt_local = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    dt_utc = dt_local.astimezone(pytz.UTC)
    return dt_local, dt_utc, _to_jd(dt_utc)


def _lon_to_sign_info(lon: float) -> dict:
    lon = lon % 360
    idx = int(lon / 30)
    return {
        "sign": SIGNS[idx],
        "sign_num": idx + 1,
        "sign_lord": SIGN_LORDS[idx + 1],
        "degree": round(lon % 30, 4),
        "longitude": round(lon, 4),
    }


def _lon_to_nakshatra_info(lon: float) -> dict:
    lon = lon % 360
    nak_span = 360 / 27
    nak_idx  = int(lon / nak_span)
    nak_deg  = lon % nak_span
    pada     = int(nak_deg / (nak_span / 4)) + 1
    return {
        "nakshatra": NAKSHATRAS[nak_idx],
        "nakshatra_num": nak_idx + 1,
        "nakshatra_lord": NAKSHATRA_LORDS[nak_idx],
        "pada": pada,
    }


def _calc_body(jd: float, body_id: int) -> tuple:
    """Return (longitude, speed) for a celestial body."""
    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
    result, _ = swe.calc_ut(jd, body_id, flags)
    return result[0] % 360, result[3]


def _ayanamsa(jd: float) -> float:
    return round(swe.get_ayanamsa_ut(jd), 6)


def _hours_remaining_in_nakshatra(moon_lon: float, moon_speed: float) -> Optional[float]:
    """Approximate hours until Moon leaves current nakshatra."""
    if moon_speed == 0:
        return None
    nak_span = 360 / 27
    deg_used = moon_lon % nak_span
    deg_remaining = nak_span - deg_used
    hours = deg_remaining / abs(moon_speed) * 24
    return round(hours, 2)


def _hours_remaining_in_tithi(tithi_angle: float, moon_speed: float) -> Optional[float]:
    """Approximate hours until Moon completes current tithi (12° arc)."""
    if moon_speed == 0:
        return None
    deg_used = tithi_angle % 12
    deg_remaining = 12 - deg_used
    hours = deg_remaining / abs(moon_speed) * 24
    return round(hours, 2)


def _karana_from_angle(tithi_angle: float) -> str:
    karana_index = int(tithi_angle / 6)
    if karana_index == 0:
        return "Kimstughna"
    elif karana_index <= 56:
        return KARANAS[1 + ((karana_index - 1) % 7)]
    elif karana_index == 57:
        return "Shakuni"
    elif karana_index == 58:
        return "Chatushpada"
    else:
        return "Naga"


def _kp_sublord(moon_lon: float) -> dict:
    """
    KP sub-lord of the Moon's nakshatra position.
    Each nakshatra (13°20') is divided into sub-lords proportional to dasha years.
    """
    nak_span = 360 / 27             # 13.333...°
    sub_span = nak_span / 120       # Each year = nak_span/120

    nak_idx   = int(moon_lon / nak_span)
    nak_start = nak_idx * nak_span
    pos_in_nak = moon_lon - nak_start   # 0 … 13.333°

    # Starting dasha lord for this nakshatra
    start_lord_idx = nak_idx % 9
    lord_order = DASHA_SEQUENCE[start_lord_idx:] + DASHA_SEQUENCE[:start_lord_idx]

    cumulative = 0.0
    for lord in lord_order:
        span = DASHA_YEARS[lord] * sub_span
        if cumulative + span > pos_in_nak:
            fraction = (pos_in_nak - cumulative) / span
            sub_remaining = (1 - fraction) * span / sub_span  # in dasha-years
            return {
                "nakshatra_lord": NAKSHATRA_LORDS[nak_idx],
                "sub_lord": lord,
                "sub_remaining_years": round(sub_remaining, 4),
            }
        cumulative += span
    return {"nakshatra_lord": NAKSHATRA_LORDS[nak_idx], "sub_lord": lord_order[-1]}


def _rahu_kala_times(sunrise_jd: float, sunset_jd: float, vara_num: int) -> dict:
    """
    Compute Rahu Kala, Gulika Kala, Yamaganda start/end as UTC ISO strings.
    Day is divided into 8 equal slots from sunrise to sunset.
    """
    day_dur = sunset_jd - sunrise_jd
    slot_dur = day_dur / 8.0

    def slot_times(slot: int) -> dict:
        start_jd = sunrise_jd + (slot - 1) * slot_dur
        end_jd   = start_jd + slot_dur
        return {"start": _jd_to_hhmm_utc(start_jd), "end": _jd_to_hhmm_utc(end_jd)}

    return {
        "rahu_kala":  slot_times(RAHU_KALA_SLOT[vara_num]),
        "gulika_kala":   slot_times(GULIKA_SLOT[vara_num]),
        "yamaganda":  slot_times(YAMAGANDA_SLOT[vara_num]),
    }


def _compute_sunrise_sunset(lat: float, lon: float, jd_start: float) -> tuple:
    """Return (sunrise_jd, sunset_jd, transit_jd) — Julian Days in UT."""
    flags = swe.FLG_SIDEREAL
    # swe.rise_trans returns (retval, result) where result[0] is JD
    try:
        rise_result = swe.rise_trans(jd_start - 0.5, swe.SUN, lon, lat,
                                     swe.CALC_RISE, 0, 0.0, 0.0)
        sunrise_jd = rise_result[1][0]

        set_result = swe.rise_trans(jd_start - 0.5, swe.SUN, lon, lat,
                                    swe.CALC_SET, 0, 0.0, 0.0)
        sunset_jd = set_result[1][0]

        noon_jd = (sunrise_jd + sunset_jd) / 2.0
        return sunrise_jd, sunset_jd, noon_jd
    except Exception:
        # Fallback: approximate sunrise/sunset at 6 AM / 6 PM local
        return jd_start + 0.25, jd_start + 0.75, jd_start + 0.5


def _jd_to_hhmm_utc(jd: float) -> str:
    try:
        # swe.jdut1_to_utc returns (year, month, day, hour, minute, second)
        y, mo, d, hr, mn, sc = swe.jdut1_to_utc(jd, 1)
        dt = datetime(int(y), int(mo), int(d), int(hr), int(mn), int(sc),
                      tzinfo=pytz.UTC)
        return dt.strftime("%H:%M UTC")
    except Exception:
        return "N/A"


# ── Public API ─────────────────────────────────────────────────────────────────

def calculate_panchanga(
    lat: float,
    lon: float,
    date_str: Optional[str] = None,
    tz_str: str = "UTC"
) -> dict:
    """
    Full Vedic Panchanga for a given date and location.

    Uses KP Krishnamurti Ayanamsha (swe.SIDM_KRISHNAMURTI).

    Returns:
        Tithi, Vara, Nakshatra (Moon), Yoga, Karana,
        KP sub-lord, Rahu Kala / Gulika / Yamaganda,
        Sun & Moon positions, ayanamsha value, auspiciousness notes.
    """
    tz_obj = _parse_tz(tz_str)
    dt_local, dt_utc, jd = _resolve_datetime(date_str, tz_str, hour=0)

    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
    sun_res,  _ = swe.calc_ut(jd, swe.SUN,  flags)
    moon_res, _ = swe.calc_ut(jd, swe.MOON, flags)

    sun_lon   = sun_res[0]  % 360
    moon_lon  = moon_res[0] % 360
    moon_speed = moon_res[3]

    # ── Tithi ──────────────────────────────────────────────────────────────────
    tithi_angle = (moon_lon - sun_lon) % 360
    tithi_index = int(tithi_angle / 12)
    tithi_name  = TITHIS[tithi_index]
    paksha      = "Shukla" if tithi_index < 15 else "Krishna"
    tithi_num   = (tithi_index % 15) + 1
    tithi_hours = _hours_remaining_in_tithi(tithi_angle, moon_speed)

    # ── Vara ───────────────────────────────────────────────────────────────────
    vara_num  = int(jd + 1.5) % 7
    vara_name = VARAS[vara_num]

    # ── Nakshatra (Moon) ───────────────────────────────────────────────────────
    nak_info   = _lon_to_nakshatra_info(moon_lon)
    nak_hours  = _hours_remaining_in_nakshatra(moon_lon, moon_speed)

    # ── Yoga ───────────────────────────────────────────────────────────────────
    yoga_angle = (sun_lon + moon_lon) % 360
    yoga_idx   = int(yoga_angle / (360 / 27))
    yoga_name  = YOGAS[yoga_idx]

    # ── Karana ─────────────────────────────────────────────────────────────────
    karana_name = _karana_from_angle(tithi_angle)

    # ── KP Sub-lord ────────────────────────────────────────────────────────────
    kp_sub = _kp_sublord(moon_lon)

    # ── Sunrise / Sunset ───────────────────────────────────────────────────────
    sunrise_jd, sunset_jd, noon_jd = _compute_sunrise_sunset(lat, lon, jd)
    sunrise_str = _jd_to_hhmm_utc(sunrise_jd)
    sunset_str  = _jd_to_hhmm_utc(sunset_jd)

    # ── Rahu Kala / Gulika / Yamaganda ─────────────────────────────────────────
    kala = _rahu_kala_times(sunrise_jd, sunset_jd, vara_num)

    # ── Sun & Moon positions ───────────────────────────────────────────────────
    sun_info  = {**_lon_to_sign_info(sun_lon),  **_lon_to_nakshatra_info(sun_lon)}
    moon_info = {**_lon_to_sign_info(moon_lon), **_lon_to_nakshatra_info(moon_lon),
                 "speed_deg_day": round(moon_speed, 4)}

    # ── Auspiciousness ─────────────────────────────────────────────────────────
    notes = []
    if tithi_name in INAUSPICIOUS_TITHIS:
        notes.append(f"{tithi_name} tithi — generally inauspicious for new beginnings")
    if yoga_name in INAUSPICIOUS_YOGAS:
        notes.append(f"{yoga_name} yoga — avoid important activities")
    if karana_name in INAUSPICIOUS_KARANAS:
        notes.append("Vishti (Bhadra) karana — inauspicious period, avoid initiations")

    # ── Ayanamsha ──────────────────────────────────────────────────────────────
    ayanamsa_val = _ayanamsa(jd)

    return {
        "date":          dt_local.date().isoformat(),
        "ayanamsha":     "KP Krishnamurti",
        "ayanamsha_value": ayanamsa_val,
        "julian_day":    round(jd, 6),
        "location":      {"lat": lat, "lon": lon, "tz": tz_str},
        "sun":           sun_info,
        "moon":          moon_info,
        "panchanga": {
            "tithi": {
                "name":           tithi_name,
                "number":         tithi_num,
                "paksha":         paksha,
                "angle":          round(tithi_angle, 4),
                "hours_remaining": tithi_hours,
            },
            "vara": {
                "name":  vara_name,
                "lord":  VARA_LORDS[vara_name],
                "num":   vara_num,
            },
            "nakshatra": {
                "name":            nak_info["nakshatra"],
                "number":          nak_info["nakshatra_num"],
                "lord":            nak_info["nakshatra_lord"],
                "pada":            nak_info["pada"],
                "hours_remaining": nak_hours,
            },
            "yoga": {
                "name":       yoga_name,
                "number":     yoga_idx + 1,
                "auspicious": yoga_name not in INAUSPICIOUS_YOGAS,
            },
            "karana": {
                "name":       karana_name,
                "auspicious": karana_name not in INAUSPICIOUS_KARANAS,
            },
            "kp_sublord": kp_sub,
        },
        "muhurta": {
            "sunrise":       sunrise_str,
            "sunset":        sunset_str,
            "rahu_kala":     kala["rahu_kala"],
            "gulika_kala":   kala["gulika_kala"],
            "yamaganda":     kala["yamaganda"],
        },
        "auspiciousness_notes": notes,
        "overall_auspicious": len(notes) == 0,
    }


def calculate_sunrise_sunset(
    lat: float,
    lon: float,
    date_str: Optional[str] = None,
    tz_str: str = "UTC"
) -> dict:
    """Return precise sunrise, sunset, and solar noon times for the given location."""
    dt_local, dt_utc, jd = _resolve_datetime(date_str, tz_str, hour=0)
    sunrise_jd, sunset_jd, noon_jd = _compute_sunrise_sunset(lat, lon, jd)

    def jd_to_local(j):
        try:
            y, mo, d, hr, mn, sc = swe.jdut1_to_utc(j, 1)
            dt_u = datetime(int(y), int(mo), int(d), int(hr), int(mn), int(sc),
                            tzinfo=pytz.UTC)
            tz_obj = _parse_tz(tz_str)
            dt_l = dt_u.astimezone(tz_obj)
            return {"utc": dt_u.strftime("%H:%M UTC"), "local": dt_l.strftime("%H:%M %Z")}
        except Exception:
            return {"utc": "N/A", "local": "N/A"}

    day_dur_hours = (sunset_jd - sunrise_jd) * 24
    night_dur_hours = 24 - day_dur_hours

    return {
        "date":       dt_local.date().isoformat(),
        "location":   {"lat": lat, "lon": lon, "tz": tz_str},
        "sunrise":    jd_to_local(sunrise_jd),
        "sunset":     jd_to_local(sunset_jd),
        "solar_noon": jd_to_local(noon_jd),
        "day_duration_hours":   round(day_dur_hours, 2),
        "night_duration_hours": round(night_dur_hours, 2),
    }


def get_moon_phase(
    date_str: Optional[str] = None,
    tz_str: str = "UTC"
) -> dict:
    """Return Moon phase details including illumination percentage and waxing/waning."""
    dt_local, dt_utc, jd = _resolve_datetime(date_str, tz_str, hour=12)

    flags = swe.FLG_SIDEREAL | swe.FLG_SPEED
    sun_res,  _ = swe.calc_ut(jd, swe.SUN,  flags)
    moon_res, _ = swe.calc_ut(jd, swe.MOON, flags)

    sun_lon  = sun_res[0]  % 360
    moon_lon = moon_res[0] % 360

    tithi_angle = (moon_lon - sun_lon) % 360
    tithi_index = int(tithi_angle / 12)

    # Illumination: 0 at new moon (0°), 100 at full moon (180°)
    illumination = round((1 - abs(tithi_angle - 180) / 180) * 100, 1)
    waxing = tithi_angle < 180

    return {
        "date":           dt_local.date().isoformat(),
        "ayanamsha":      "KP Krishnamurti",
        "moon_longitude": round(moon_lon, 4),
        "sun_longitude":  round(sun_lon, 4),
        "tithi_angle":    round(tithi_angle, 4),
        "tithi_name":     TITHIS[tithi_index],
        "paksha":         "Shukla" if tithi_index < 15 else "Krishna",
        "illumination_pct": illumination,
        "waxing":         waxing,
        "moon_sign":      _lon_to_sign_info(moon_lon)["sign"],
        "moon_nakshatra": _lon_to_nakshatra_info(moon_lon)["nakshatra"],
        "kp_sublord":     _kp_sublord(moon_lon),
    }


def get_hora_chart(
    date_str: Optional[str] = None,
    tz_str: str = "UTC"
) -> dict:
    """
    Return the Hora (hourly planetary rulership) chart for the day.
    Each day is divided into 24 hours; lord alternates in a specific pattern.
    """
    dt_local, dt_utc, jd = _resolve_datetime(date_str, tz_str, hour=0)

    vara_num  = int(jd + 1.5) % 7
    vara_name = VARAS[vara_num]
    vara_lord = VARA_LORDS[vara_name]

    # Hora sequence starts with vara lord at sunrise
    # Order: Sun, Venus, Mercury, Moon, Saturn, Jupiter, Mars (repeating)
    hora_seq = ["Sun","Venus","Mercury","Moon","Saturn","Jupiter","Mars"]
    start_idx = hora_seq.index(vara_lord)

    horas = []
    for i in range(24):
        lord = hora_seq[(start_idx + i) % 7]
        horas.append({"hour": i, "lord": lord})

    return {
        "date":      dt_local.date().isoformat(),
        "vara":      vara_name,
        "vara_lord": vara_lord,
        "horas":     horas,
    }


# ── Standalone test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    print("=== Panchanga for London (today) ===")
    result = calculate_panchanga(lat=51.5074, lon=-0.1278, tz_str="Europe/London")
    print(json.dumps(result, indent=2))
    print("\n=== Moon Phase ===")
    moon = get_moon_phase(tz_str="UTC")
    print(json.dumps(moon, indent=2))
