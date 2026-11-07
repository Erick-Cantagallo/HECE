# HECE/src/hece/lawchecks.py
"""
Physical laws checked with arithmetic, not with the model's opinion.

Only claims that can be extracted unambiguously are checked. When a claim is found and the numbers break the law,
the result is a VERIFIED violation (the evidence is the calculation itself).
"""
import re
from typing import List, Tuple

_TEMPERATURE = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*(?:(K|kelvin)\b|(?:°\s?|degrees?\s+)?(C|celsius)\b)", re.I)
_EFFICIENCY = [
    re.compile(r"(?:thermal|conversion|cycle|heat[- ]to[- ](?:work|power|electricity))\s+efficiency\s+(?:of\s+)?"
               r"(?:at least\s+|about\s+|around\s+|roughly\s+|up to\s+|over\s+|above\s+|of\s+)?"
               r"(\d+(?:\.\d+)?)\s*(?:%|percent)", re.I),
    re.compile(r"convert\w*\s+(\d+(?:\.\d+)?)\s*(?:%|percent)\s+of\s+(?:the\s+)?(?:[\w-]+\s+){0,2}heat\s+"
               r"(?:into|to)\s+(?:electricity|electrical|work|power|mechanical)", re.I),
]
_CARNOT_TOLERANCE = 0.005


def _temperatures_kelvin(text: str) -> List[float]:
    temps = []
    for m in _TEMPERATURE.finditer(text):
        value = float(m.group(1))
        kelvin = value if m.group(2) else value + 273.15
        if kelvin > 0:
            temps.append(kelvin)
    return temps


def carnot_limit(hot_k: float, cold_k: float) -> float:
    return 1.0 - cold_k / hot_k


def find_carnot_violations(text: str) -> List[Tuple[str, str]]:
    """
    Heat-to-work efficiency claims above the Carnot limit of the temperatures the text itself states.
    Uses the widest temperature span in the text (the most lenient limit), so a hit is a genuine violation.
    Returns (law, evidence) pairs.
    """
    temps = _temperatures_kelvin(text or "")
    if len(set(round(t, 2) for t in temps)) < 2:
        return []
    hot, cold = max(temps), min(temps)
    limit = carnot_limit(hot, cold)
    for pattern in _EFFICIENCY:
        for m in pattern.finditer(text):
            claimed = float(m.group(1)) / 100
            if claimed > limit + _CARNOT_TOLERANCE:
                evidence = (f"claims {claimed * 100:.0f}% heat-to-work efficiency ('{' '.join(m.group(0).split())}') "
                            f"between {hot:.0f} K and {cold:.0f} K, but the Carnot limit 1 - Tc/Th is "
                            f"{limit * 100:.1f}%")
                return [("Second Law of Thermodynamics (Carnot limit)", evidence)]
    return []
