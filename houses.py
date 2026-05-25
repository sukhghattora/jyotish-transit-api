"""
houses.py — Whole Sign house calculation for Vedic (Jyotish) astrology.

Whole Sign system (traditional Vedic):
    - The entire sign containing the Lagna is house 1.
    - Each successive sign is the next house.
    - Formula: house = ((planet_sign_index - lagna_sign_index) % 12) + 1

Example: Sagittarius Lagna -> Sagittarius=1, Capricorn=2, ..., Pisces=4, ...
"""

from typing import Dict

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SIGN_INDEX = {s: i for i, s in enumerate(SIGNS)}


def sign_to_abs(sign: str, degree: float) -> float:
    """Convert a sign + degree-in-sign to absolute ecliptic degrees (0-360)."""
    idx = SIGN_INDEX.get(sign)
    if idx is None:
        raise ValueError(f"Unknown sign: {sign}")
    return idx * 30.0 + degree


def calculate_houses(
    positions: Dict[str, Dict],
    lagna_sign: str,
    lagna_degree: float,   # kept for API compatibility; not used in Whole Sign
) -> Dict[str, Dict]:
    """
    Given planet positions {planet: {sign, degree}} and the Lagna sign,
    return {planet: {sign, degree, house}} using the Whole Sign house system.

    Whole Sign is the traditional Jyotish system:
    the entire Lagna sign = house 1, next sign = house 2, etc.
    """
    lagna_idx = SIGN_INDEX.get(lagna_sign)
    if lagna_idx is None:
        raise ValueError(f"Unknown lagna sign: {lagna_sign}")

    result = {}
    for planet, data in positions.items():
        planet_idx = SIGN_INDEX.get(data["sign"])
        if planet_idx is None:
            raise ValueError(f"Unknown sign '{data['sign']}' for planet {planet}")

        house = (planet_idx - lagna_idx) % 12 + 1
        result[planet] = {
            "sign":   data["sign"],
            "degree": data["degree"],
            "house":  house,
        }

    return result
