# HECE/src/hece/dimensions.py
"""
Minimal SI dimensional analysis.

Used to sanity-check the units a hypothesis declares for a postulated physical quantity,
and to notice when a "new" quantity is dimensionally identical to a known one.
Tip: write units with parentheses when dividing, e.g. J/(kg K).
"""
import re
from fractions import Fraction
from typing import List, Optional, Tuple

Dim = Tuple[Fraction, ...]  # exponents of (kg, m, s, A, K, mol, cd)
BASE_ORDER = ("kg", "m", "s", "A", "K", "mol", "cd")


def _d(m=0, l=0, t=0, i=0, k=0, n=0, j=0) -> Dim:
    return tuple(Fraction(x) for x in (m, l, t, i, k, n, j))


ZERO: Dim = _d()

_UNITS = {
    "kg": _d(m=1), "g": _d(m=1), "m": _d(l=1), "s": _d(t=1), "A": _d(i=1), "K": _d(k=1),
    "mol": _d(n=1), "cd": _d(j=1),
    "N": _d(1, 1, -2), "J": _d(1, 2, -2), "eV": _d(1, 2, -2), "W": _d(1, 2, -3),
    "Pa": _d(1, -1, -2), "bar": _d(1, -1, -2), "atm": _d(1, -1, -2),
    "Hz": _d(t=-1), "Bq": _d(t=-1), "C": _d(t=1, i=1), "V": _d(1, 2, -3, -1),
    "ohm": _d(1, 2, -3, -2), "Ω": _d(1, 2, -3, -2), "F": _d(-1, -2, 4, 2),
    "T": _d(1, 0, -2, -1), "Wb": _d(1, 2, -2, -1), "H": _d(1, 2, -2, -2), "S": _d(-1, -2, 3, 2),
    "L": _d(l=3), "rad": ZERO, "sr": ZERO,
}
_PREFIXES = set("yzafpnuµμmcdkMGTPE")

_KNOWN = [
    (_d(1, 2, -2), "energy or torque"), (_d(1, 1, -2), "force"), (_d(1, 2, -3), "power"),
    (_d(1, -1, -2), "pressure or energy density"), (_d(t=-1), "frequency or rate"),
    (_d(1, 1, -1), "momentum"), (_d(1, 2, -1), "angular momentum or action"),
    (_d(l=1, t=-1), "velocity"), (_d(l=1, t=-2), "acceleration"), (_d(m=1), "mass"),
    (_d(l=1), "length"), (_d(t=1), "time"), (_d(k=1), "temperature"),
    (_d(1, 2, -2, 0, -1), "entropy or heat capacity"), (_d(t=1, i=1), "electric charge"),
    (_d(1, 2, -3, -1), "voltage"), (_d(1, 2, -3, -2), "resistance"), (_d(-1, -2, 4, 2), "capacitance"),
    (_d(1, 0, -2, -1), "magnetic flux density"), (_d(1, 1, -3, -1), "electric field"),
    (_d(1, -3), "mass density"), (_d(1, 0, -3), "intensity (power per area)"),
    (_d(l=2, t=-2), "specific energy"), (_d(i=1), "electric current"),
]

_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")
_SUP_RUN = re.compile(r"[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+")
_TOKEN = re.compile(r"(\s*)(\*\*|\^|\(|\)|\*|/|-|\+|\d+(?:\.\d+)?|[A-Za-zµμΩ]+)")


def _normalize(text: str) -> str:
    s = _SUP_RUN.sub(lambda m: "^" + m.group(0).translate(_SUPERSCRIPTS), text)
    for a, b in (("·", "*"), ("⋅", "*"), ("×", "*"), ("−", "-"), ("–", "-")):
        s = s.replace(a, b)
    return s.strip()


def _lex(s: str):
    tokens, pos = [], 0
    while pos < len(s):
        m = _TOKEN.match(s, pos)
        if not m:
            raise ValueError(f"bad character at {pos}")
        tokens.append((m.group(2), bool(m.group(1))))  # (text, had_space_before)
        pos = m.end()
    return tokens


def _unit(name: str) -> Dim:
    if name in _UNITS:
        return _UNITS[name]
    if len(name) > 1 and name[0] in _PREFIXES and name[1:] in _UNITS:
        return _UNITS[name[1:]]
    raise ValueError(f"unknown unit '{name}'")


def _mul(a: Dim, b: Dim) -> Dim:
    return tuple(x + y for x, y in zip(a, b))


def _div(a: Dim, b: Dim) -> Dim:
    return tuple(x - y for x, y in zip(a, b))


def _pow(a: Dim, e: Fraction) -> Dim:
    return tuple(x * e for x in a)


class _Parser:
    def __init__(self, tokens):
        self.t = tokens
        self.p = 0

    def peek(self):
        return self.t[self.p] if self.p < len(self.t) else None

    def expr(self) -> Dim:
        result = self.term()
        while True:
            tok = self.peek()
            if tok is None or tok[0] == ")":
                return result
            if tok[0] in ("*",):
                self.p += 1
                result = _mul(result, self.term())
            elif tok[0] == "/":
                self.p += 1
                result = _div(result, self.term())
            else:  # implicit multiplication ("kg m s")
                result = _mul(result, self.term())

    def term(self) -> Dim:
        base = self.atom()
        tok = self.peek()
        if tok and tok[0] in ("^", "**"):
            self.p += 1
            return _pow(base, self.number())
        # compact exponent written without a caret: "m2", "s-2"
        if tok and not tok[1] and self._is_unit_atom:
            if re.fullmatch(r"\d+", tok[0]):
                self.p += 1
                return _pow(base, Fraction(tok[0]))
            if tok[0] in ("-", "+") and self.p + 1 < len(self.t) and not self.t[self.p + 1][1] \
                    and re.fullmatch(r"\d+", self.t[self.p + 1][0]):
                self.p += 1
                return _pow(base, self.number(sign=tok[0]))
        return base

    def number(self, sign: str = "") -> Fraction:
        tok = self.peek()
        if tok and tok[0] == "(":                      # exponent in parentheses: C^(-2)
            self.p += 1
            value = self.number()
            closing = self.peek()
            if not closing or closing[0] != ")":
                raise ValueError("missing ) after exponent")
            self.p += 1
            return value
        if tok and tok[0] in ("-", "+"):
            sign = tok[0]
            self.p += 1
            tok = self.peek()
        if not tok or not re.fullmatch(r"\d+(?:\.\d+)?", tok[0]):
            raise ValueError("exponent expected")
        self.p += 1
        value = Fraction(tok[0])
        return -value if sign == "-" else value

    def atom(self) -> Dim:
        tok = self.peek()
        self._is_unit_atom = False
        if tok is None:
            raise ValueError("unexpected end")
        self.p += 1
        if tok[0] == "(":
            inner = self.expr()
            closing = self.peek()
            if not closing or closing[0] != ")":
                raise ValueError("missing )")
            self.p += 1
            return inner
        if re.fullmatch(r"\d+(?:\.\d+)?", tok[0]):
            return ZERO
        if re.fullmatch(r"[A-Za-zµμΩ]+", tok[0]):
            self._is_unit_atom = True
            return _unit(tok[0])
        raise ValueError(f"unexpected '{tok[0]}'")


def parse_dimensions(text: str) -> Optional[Dim]:
    """Parses a unit expression such as 'kg m^2 s^-2' or 'J/(kg K)'. Returns None if it cannot."""
    s = _normalize(str(text or ""))
    if not s:
        return None
    if s.lower().strip("() ") in {"dimensionless", "1", "unitless", "none", "-"}:
        return ZERO
    result = _parse_clean(s)
    if result is None:
        # models often add a descriptive word in parentheses: "J (joules)", "W (watts)"
        stripped = re.sub(r"\(\s*[A-Za-z][A-Za-z ,.\-]{3,}\)", " ", s).strip()
        if stripped and stripped != s:
            result = _parse_clean(stripped)
    return result


def _parse_clean(s: str) -> Optional[Dim]:
    try:
        parser = _Parser(_lex(s))
        dim = parser.expr()
        return dim if parser.p == len(parser.t) else None
    except (ValueError, ZeroDivisionError):
        return None


def describe(dim: Dim) -> str:
    parts: List[str] = []
    for name, exp in zip(BASE_ORDER, dim):
        if exp != 0:
            parts.append(name if exp == 1 else f"{name}^{exp}")
    return " ".join(parts) if parts else "dimensionless"


def same_dimension_as(dim: Dim) -> Optional[str]:
    """Name of a well-known quantity with exactly these dimensions, if any."""
    for known, name in _KNOWN:
        if known == dim:
            return name
    return None
