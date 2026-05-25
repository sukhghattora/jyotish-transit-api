"""
test_transits.py — Unit tests for house calculation logic.

Run:  python -m pytest test_transits.py -v
"""

import pytest
from houses import sign_to_abs, calculate_houses, SIGNS


# ── sign_to_abs ───────────────────────────────────────────────────────────────

def test_sign_to_abs_aries_0():
    assert sign_to_abs("Aries", 0) == 0.0

def test_sign_to_abs_aries_15():
    assert sign_to_abs("Aries", 15) == 15.0

def test_sign_to_abs_taurus_0():
    assert sign_to_abs("Taurus", 0) == 30.0

def test_sign_to_abs_sagittarius_12():
    # Sagittarius is index 8 → 8 * 30 = 240
    assert sign_to_abs("Sagittarius", 12.5) == 252.5

def test_sign_to_abs_pisces_0():
    # Pisces is index 11 → 11 * 30 = 330
    assert sign_to_abs("Pisces", 0) == 330.0

def test_sign_to_abs_unknown():
    with pytest.raises(ValueError, match="Unknown sign"):
        sign_to_abs("Ophiuchus", 5)


# ── House calculations (Sagittarius Lagna 12.5°) ─────────────────────────────
# Lagna abs = 252.5°

SAGITTARIUS_LAGNA = ("Sagittarius", 12.5)

def house(sign, degree):
    positions = {"planet": {"sign": sign, "degree": degree}}
    result = calculate_houses(positions, *SAGITTARIUS_LAGNA)
    return result["planet"]["house"]


def test_saturn_pisces_house_4():
    """Saturn in Pisces → house 4 from Sagittarius Lagna."""
    # Pisces abs ≈ 330+2 = 332; diff = (332 - 252.5) % 360 = 79.5; house = floor(79.5/30)+1 = 3+1 = 4 ✓
    assert house("Pisces", 2.23) == 4

def test_jupiter_gemini_house_7():
    """Jupiter in Gemini -> house 7 from Sagittarius Lagna (Whole Sign)."""
    # Sagittarius=1, Capricorn=2, Aquarius=3, Pisces=4, Aries=5, Taurus=6, Gemini=7
    assert house("Gemini", 8.91) == 7

def test_sun_gemini_house_7():
    """Sun in Gemini -> house 7 from Sagittarius Lagna (Whole Sign)."""
    assert house("Gemini", 4.23) == 7

def test_lagna_itself_is_house_1():
    """A planet exactly at lagna degree should be in house 1."""
    assert house("Sagittarius", 12.5) == 1

def test_planet_30_degrees_ahead_is_house_2():
    """A planet 30° ahead of lagna is in house 2."""
    # Sagittarius 12.5 + 30 = Capricorn 12.5
    assert house("Capricorn", 12.5) == 2

def test_planet_180_degrees_ahead_is_house_7():
    """A planet exactly opposite the lagna is in house 7."""
    # Sagittarius 12.5 opposite = Gemini 12.5
    assert house("Gemini", 12.5) == 7

def test_planet_330_degrees_ahead_is_house_12():
    """A planet 330° ahead (30° behind) lagna is in house 12."""
    # Sagittarius 12.5 - 30 = Scorpio 12.5
    assert house("Scorpio", 12.5) == 12


# ── calculate_houses returns correct structure ─────────────────────────────────

def test_full_output_structure():
    positions = {
        "sun":     {"sign": "Gemini",  "degree": 4.23},
        "saturn":  {"sign": "Pisces",  "degree": 2.23},
        "jupiter": {"sign": "Gemini",  "degree": 8.91},
    }
    result = calculate_houses(positions, "Sagittarius", 12.5)

    for planet, data in result.items():
        assert "sign"   in data
        assert "degree" in data
        assert "house"  in data
        assert 1 <= data["house"] <= 12

def test_all_signs_covered():
    """All 12 SIGNS should be valid inputs."""
    for sign in SIGNS:
        result = calculate_houses({"p": {"sign": sign, "degree": 0}}, "Aries", 0)
        assert 1 <= result["p"]["house"] <= 12
