# HECE/src/hece/numerics.py
"""
Deterministic arithmetic check on the numbers a hypothesis writes.

Language models state equivalences such as "300 m/s, which is 0.01c" or "30 kHz (30,000 Hz)" and often get them wrong.
This module finds statements where the SAME quantity is written twice with explicit equivalence wording, converts both
sides to SI and reports the ones that disagree. It only compares quantities of identical dimension, so it cannot
misfire on unrelated numbers, and it only trusts explicit markers ("which is", "i.e.", "=", "approximately") plus the
"<speed> (<fraction of c>)" form, because a bare "(2 mm)" usually adds a different quantity.
"""
import re
from typing import List, Optional, Tuple

from hece.dimensions import Dim, parse_dimensions

C_LIGHT = 299792458.0
TOLERANCE = 0.15   # relative; the model rounds ("approximately")

_PREFIX = {"y": 1e-24, "z": 1e-21, "a": 1e-18, "f": 1e-15, "p": 1e-12, "n": 1e-9, "u": 1e-6, "µ": 1e-6, "μ": 1e-6,
           "m": 1e-3, "c": 1e-2, "d": 1e-1, "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "P": 1e15}
# scale to SI for each unit symbol (dimensions come from hece.dimensions)
_SCALE = {"kg": 1.0, "g": 1e-3, "m": 1.0, "s": 1.0, "A": 1.0, "K": 1.0, "mol": 1.0, "cd": 1.0, "N": 1.0, "J": 1.0,
          "eV": 1.602176634e-19, "W": 1.0, "Pa": 1.0, "bar": 1e5, "atm": 101325.0, "Hz": 1.0, "C": 1.0, "V": 1.0,
          "F": 1.0, "T": 1.0, "H": 1.0, "S": 1.0, "L": 1e-3}

_WORDS = [
    (r"\bkilometers? per second\b|\bkilometres? per second\b", "km/s"),
    (r"\bmeters? per second\b|\bmetres? per second\b", "m/s"),
    (r"\bkilohertz\b", "kHz"), (r"\bmegahertz\b", "MHz"), (r"\bgigahertz\b", "GHz"), (r"\bhertz\b", "Hz"),
    (r"\bmicrometers?\b|\bmicrometres?\b|\bmicrons?\b", "µm"), (r"\bnanometers?\b|\bnanometres?\b", "nm"),
    (r"\bmillimeters?\b|\bmillimetres?\b", "mm"), (r"\bcentimeters?\b|\bcentimetres?\b", "cm"),
    (r"\bkilometers?\b|\bkilometres?\b", "km"), (r"\bmeters?\b|\bmetres?\b", "m"),
    (r"\bmilliseconds?\b", "ms"), (r"\bmicroseconds?\b", "µs"), (r"\bnanoseconds?\b", "ns"), (r"\bseconds?\b", "s"),
    (r"\bjoules?\b", "J"), (r"\bwatts?\b", "W"), (r"\bpascals?\b", "Pa"), (r"\bkelvins?\b", "K"),
    (r"\btimes the speed of light\b", "c"),
]
_NUM = r"\d[\d,]*(?:\.\d+)?(?:\s*(?:x|\u00d7)\s*10\^?-?\d+|[eE]-?\d+)?"
_SYM = r"(?:kg|mol|cd|bar|atm|[yzafpnuµμmcdkMGTP]?(?:Hz|eV|Pa)|[yzafpnuµμmcdkMGTP]?(?:g|m|s|A|K|N|J|W|C|V|F|H|S|T|L))"
_UNIT = rf"(?:{_SYM}|c)(?:\^-?\d+)?(?:/{_SYM}(?:\^-?\d+)?)?"
_FILLER = r"(?:\s+[A-Za-z]+){0,2}"
_MARK = (r"(?:\s*\([^()\d]*\))?\s*(?:,?\s*(?:which is|i\.e\.,?|equivalent to|equal to|or about|or roughly|"
         r"approximately|roughly|about|\u2248|~|=)\s*)")
_PAIR = re.compile(rf"(?P<n1>{_NUM})\s*(?P<u1>{_UNIT})\b{_FILLER}{_MARK}(?P<n2>{_NUM})\s*(?P<u2>{_UNIT})\b")
_PAREN_C = re.compile(rf"(?P<n1>{_NUM})\s*(?P<u1>{_UNIT})\b\s*\(\s*(?:\u2248|~|about|approximately)?\s*(?P<n2>{_NUM})\s*(?P<u2>c)\b")


def _number(text: str) -> float:
    t = text.replace(",", "")
    m = re.match(r"([\d.]+)\s*(?:x|\u00d7)\s*10\^?(-?\d+)", t)
    return float(m.group(1)) * 10 ** int(m.group(2)) if m else float(t)


def _one(sym: str) -> Optional[Tuple[Dim, float]]:
    """Dimension and SI scale of a single unit symbol with optional ^exponent (c = speed of light)."""
    m = re.fullmatch(r"(.+?)(?:\^(-?\d+))?", sym)
    base, exp = m.group(1), int(m.group(2) or 1)
    if base == "c":
        dim, scale = parse_dimensions("m/s"), C_LIGHT
    elif base in _SCALE:
        dim, scale = parse_dimensions("kg" if base == "g" else base), _SCALE[base]
    elif len(base) > 1 and base[0] in _PREFIX and base[1:] in _SCALE and base != "kg":
        dim, scale = parse_dimensions("kg" if base[1:] == "g" else base[1:]), _PREFIX[base[0]] * _SCALE[base[1:]]
    else:
        return None
    if dim is None:
        return None
    return tuple(x * exp for x in dim), scale ** exp


def unit_si(unit: str) -> Optional[Tuple[Dim, float]]:
    """('km/s') -> (dimension, factor to SI). Supports one unit or one 'a/b' ratio."""
    parts = unit.split("/")
    if len(parts) > 2:
        return None
    top = _one(parts[0])
    if top is None:
        return None
    if len(parts) == 1:
        return top
    bottom = _one(parts[1])
    if bottom is None:
        return None
    return tuple(a - b for a, b in zip(top[0], bottom[0])), top[1] / bottom[1]


_SUP = str.maketrans("\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207a\u207b", "0123456789+-")
_SUP_RUN = re.compile(r"[\u2070\u00b9\u00b2\u00b3\u2074-\u2079\u207a\u207b]+")


def _plain(text: str) -> str:
    out = _SUP_RUN.sub(lambda m: "^" + m.group(0).translate(_SUP), text)   # cm\u00b3 -> cm^3, s\u207b\u00b2 -> s^-2
    for pattern, repl in _WORDS:
        out = re.sub(pattern, repl, out, flags=re.I)
    return out


def find_numeric_inconsistencies(text: str) -> List[str]:
    """Statements that write one quantity twice with different values. Empty list = nothing wrong found."""
    plain = _plain(text or "")
    found: List[str] = []
    seen = set()
    for pattern in (_PAIR, _PAREN_C):
        for m in pattern.finditer(plain):
            key = (m.start("n1"), m.start("n2"))
            if key in seen:
                continue
            seen.add(key)
            a, b = unit_si(m.group("u1")), unit_si(m.group("u2"))
            if a is None or b is None or a[0] != b[0]:
                continue
            try:
                v1, v2 = _number(m.group("n1")) * a[1], _number(m.group("n2")) * b[1]
            except ValueError:
                continue
            if v1 <= 0 or v2 <= 0:
                continue
            if abs(v1 - v2) / max(v1, v2) > TOLERANCE:
                n1, u1, n2, u2 = m.group("n1"), m.group("u1"), m.group("n2"), m.group("u2")
                hint = f" ({n1} {u1} = {v1 / b[1]:.3g} {u2})" if b[1] else ""
                found.append(f"'{n1} {u1}' is written as equal to '{n2} {u2}', but they differ{hint}")
    return found


# ----------------------------------------------------------------------------------------------
# Scale check: the region a prediction claims vs the size of the components that are described
# ----------------------------------------------------------------------------------------------
_VOLUME_UNITS = {"cm^3": 1e-6, "cm3": 1e-6, "mm^3": 1e-9, "m^3": 1.0, "µm^3": 1e-18, "μm^3": 1e-18, "um^3": 1e-18, "nm^3": 1e-27,
                 "l": 1e-3, "ml": 1e-6}
_VOLUME = re.compile(rf"(?P<n>{_NUM})\s*(?P<u>cm\^3|cm3|mm\^3|[µμ]m\^3|um\^3|nm\^3|m\^3|mL|L)\b(?!\s*\^)")
_LENGTH = re.compile(rf"(?P<a>{_NUM})(?:\s*(?:-|\u2013|to)\s*(?P<b>{_NUM}))?\s*(?P<u>nm|[µμ]m|um|mm|cm|km|m)\b(?!\s*[\^/])")
_LENGTH_SCALE = {"nm": 1e-9, "µm": 1e-6, "μm": 1e-6, "um": 1e-6, "mm": 1e-3, "cm": 1e-2, "m": 1.0, "km": 1e3}
_SCALING_WORDS = re.compile(
    r"\b(?:arrays?|lattices?|stack(?:s|ed)?|grids?|tiled|tiling|networks? of|millions?|billions?|thousands? of|"
    r"scal(?:ed|able|ing)|bulk|macroscopic|wafers?|substrates?)\b", re.I)
SCALE_RATIO_LIMIT = 100.0


def find_scale_mismatch(text: str) -> List[str]:
    """
    Flags a hypothesis whose prediction claims a region far larger than every component it describes
    (for example a 1 cm^3 region from parts that are all 1-10 micrometres) when no array or scaling is described.
    """
    raw = text or ""
    raw = re.sub(r"\bcubic centimet(?:er|re)s?\b", "cm^3", raw, flags=re.I)     # before _plain turns 'centimetre' into 'cm'
    raw = re.sub(r"\bcubic millimet(?:er|re)s?\b", "mm^3", raw, flags=re.I)
    raw = re.sub(r"\bcubic met(?:er|re)s?\b", "m^3", raw, flags=re.I)
    plain = _plain(raw)
    m = re.search(r"\bPrediction:", plain)
    if not m:
        return []
    mechanism, prediction = plain[:m.start()], plain[m.start():]
    volumes = []
    for v in _VOLUME.finditer(prediction):
        try:
            unit = v.group("u")
            volumes.append(_number(v.group("n")) * _VOLUME_UNITS["l" if unit == "L" else unit.lower() if unit != "mL" else "ml"])
        except (ValueError, KeyError):
            continue
    if not volumes or _SCALING_WORDS.search(mechanism):
        return []
    sizes = []
    for l in _LENGTH.finditer(mechanism):
        try:
            high = max(_number(l.group("a")), _number(l.group("b")) if l.group("b") else 0.0)
            sizes.append(high * _LENGTH_SCALE[l.group("u")])
        except (ValueError, KeyError):
            continue
    if not sizes:
        return []
    claimed = max(volumes) ** (1.0 / 3.0)
    largest = max(sizes)
    if largest > 0 and claimed / largest > SCALE_RATIO_LIMIT * (1 + 1e-6):   # tolerance: 1e-3 / 1e-5 is not 100.0000001
        return [f"scale mismatch: the prediction claims a region about {claimed * 100:.2g} cm across, but the largest "
                f"component described is {largest * 1e6:.3g} \u00b5m ({claimed / largest:.0f}x smaller) and no array or scaling is described"]
    return []
