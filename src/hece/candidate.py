# HECE/src/hece/candidate.py
"""
Structured format for inventor-mode hypotheses.

The model answers in labelled lines (not JSON: small local models break JSON often).
Python parses and validates the structure deterministically:
  TITLE / FAMILY / MECHANISM / [NEW QUANTITY ...] / PREDICTION / REFUTATION
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from hece.dimensions import parse_dimensions, describe, same_dimension_as

MIN_MECHANISM_WORDS = 30
MIN_PREDICTION_WORDS = 8
MAX_POSTULATES = 2

_LABEL = re.compile(
    r"^\s*(?:[-*\u2022#>]+\s*|\d+[.)]\s*)?(TITLE|FAMILY|MECHANISM|NEW QUANTITY|PREDICTION|REFUTATION)\s*:\s*(.*)$",
    re.I)
_FIELD = re.compile(
    r"^\s*(DIMENSIONS?|DEFINITION|COUPLING|SYMBOL|EQUATION|MAGNITUDE|"
    r"REDUCES TO KNOWN PHYSICS WHEN|REDUCES TO|DIFFERS FROM KNOWN QUANTITY BY|DIFFERS FROM KNOWN BY|DIFFERS BY)"
    r"\s*:\s*(.*)$", re.I)
_NONE_NAMES = {"none", "n/a", "no", "-", "nil", "not applicable", ""}
_REQUIREMENT = re.compile(r"^\s*(?:[-*\u2022#>]+\s*|\d+[.)]\s*)?REQUIREMENT\s*:\s*(.+?)\s*$", re.I)
_GREEK_NAMES = {"\u03b1": "alpha", "\u03b2": "beta", "\u03b3": "gamma", "\u03b4": "delta", "\u03b5": "epsilon", "\u03b6": "zeta",
                "\u03b7": "eta", "\u03b8": "theta", "\u03ba": "kappa", "\u03bb": "lambda", "\u03bc": "mu", "\u03bd": "nu",
                "\u03be": "xi", "\u03c0": "pi", "\u03c1": "rho", "\u03c3": "sigma", "\u03c4": "tau", "\u03c6": "phi",
                "\u03d5": "phi", "\u03c7": "chi", "\u03c8": "psi", "\u03c9": "omega", "\u0393": "gamma", "\u0394": "delta",
                "\u0398": "theta", "\u039b": "lambda", "\u03a0": "pi", "\u03a3": "sigma", "\u03a6": "phi", "\u03a8": "psi",
                "\u03a9": "omega"}
_SELF_REFERENCE = re.compile(
    r"\b(?:as before|remains? unchanged|remain the same|same (?:dimensions|materials|design|setup|components?) as|"
    r"(?:the )?(?:earlier|previous|original|first) (?:design|candidate|version|iteration|attempt)|builds? (?:up)?on the earlier|"
    r"maintains? the core idea|(?:refined|improved|updated) version of)\b", re.I)
_STANDALONE_NUMBER = re.compile(r"(?<![\w^/])\d+(?:\.\d+)?(?:[eE]-?\d+|\s*[x\u00d7]\s*10\^?-?\d+)?(?![\w^])")
_CONSTRAINT_STYLE = re.compile(
    r"less than or equal to the|no more than the|must not exceed|cannot exceed|not exceed the|within the .{0,40}(?:limit|bounds)|"
    r"greater than or equal to the .{0,40}surrounding|lower than or equal to the .{0,40}surrounding", re.I)
_NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?(?:\s*[x\u00d7*]\s*10\s*\^?\s*[-+]?\d+|\s*[eE][-+]?\d+|\s*\^\s*[-+]?\d+)?")


@dataclass
class Postulate:
    name: str = ""
    symbol: str = ""
    dimensions: str = ""
    definition: str = ""
    equation: str = ""
    magnitude: str = ""
    coupling: str = ""
    reduces_to: str = ""
    differs_by: str = ""


@dataclass
class Candidate:
    title: str = ""
    family: str = ""
    mechanism: str = ""
    postulates: List[Postulate] = field(default_factory=list)
    prediction: str = ""
    refutation: str = ""
    raw: str = ""


def _ascii(text: str) -> str:
    """Lower-case with Greek letters spelled out, so 'phi' and the Greek phi count as the same symbol."""
    return "".join(_GREEK_NAMES.get(ch, ch) for ch in text).lower()


def _words(text: str) -> int:
    return len(re.findall(r"\w+", text or ""))


def _parse_postulate(text: str) -> Optional[Postulate]:
    pieces = [p.strip() for p in text.split("|")]
    name = pieces[0] if pieces else ""
    if name.lower() in _NONE_NAMES:
        return None
    p = Postulate(name=name)
    for piece in pieces[1:]:
        m = _FIELD.match(piece)
        if not m:
            continue
        key, value = m.group(1).upper(), m.group(2).strip()
        if key.startswith("DIMENSION"):
            p.dimensions = value
        elif key == "DEFINITION":
            p.definition = value
        elif key == "COUPLING":
            p.coupling = value
        elif key == "SYMBOL":
            p.symbol = value
        elif key == "EQUATION":
            p.equation = value
        elif key == "MAGNITUDE":
            p.magnitude = value
        elif key.startswith("DIFFERS"):
            p.differs_by = value
        else:
            p.reduces_to = value
    return p


def parse_candidate(text: str) -> Candidate:
    """Parses the labelled format. Unknown or missing sections simply stay empty (see validate_candidate)."""
    clean = (text or "").replace("**", "")
    entries: List[Tuple[str, List[str]]] = []
    for line in clean.splitlines():
        m = _LABEL.match(line)
        if m:
            entries.append((m.group(1).upper(), [m.group(2).strip()]))
        elif entries and line.strip():
            entries[-1][1].append(line.strip())

    cand = Candidate(raw=text or "")
    for label, chunks in entries:
        value = " ".join(c for c in chunks if c).strip()
        if label == "TITLE" and not cand.title:
            cand.title = value
        elif label == "FAMILY" and not cand.family:
            cand.family = value
        elif label == "MECHANISM" and not cand.mechanism:
            cand.mechanism = value
        elif label == "PREDICTION" and not cand.prediction:
            cand.prediction = value
        elif label == "REFUTATION" and not cand.refutation:
            cand.refutation = value
        elif label == "NEW QUANTITY":
            post = _parse_postulate(value)
            if post:
                cand.postulates.append(post)
    return cand


def _keyword_overlap(a: str, b: str) -> float:
    ta, tb = set(re.findall(r"[a-z]{4,}", a.lower())), set(re.findall(r"[a-z]{4,}", b.lower()))
    return len(ta & tb) / max(1, len(ta | tb))


def screen_requirement(text: str, laws: Optional[List[str]] = None) -> Optional[str]:
    """Why a requirement is not usable (or None). Requirements are goals to ACHIEVE, not limits to respect."""
    if not _STANDALONE_NUMBER.search(text):
        return "no numeric target"
    if _CONSTRAINT_STYLE.search(text):
        return "it is a limit that must not be broken, not an effect to achieve"
    for law in laws or []:
        clean = re.sub(r"^MUST NOT VIOLATE:\s*", "", law)
        if _keyword_overlap(text, clean) >= 0.3:
            return f"it restates a law ({clean[:40]})"
    return None


def split_requirements(text: str, max_n: int = 4, laws: Optional[List[str]] = None) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Parses 'REQUIREMENT:' lines (>= 8 words, no near-duplicates) and screens them: (accepted, [(text, reason)])."""
    accepted: List[str] = []
    rejected: List[Tuple[str, str]] = []
    for line in (text or "").replace("**", "").splitlines():
        m = _REQUIREMENT.match(line)
        if not m or _words(m.group(1)) < 8:
            continue
        req = m.group(1).strip()
        if laws is not None:
            reason = screen_requirement(req, laws)
            if reason:
                rejected.append((req, reason))
                continue
        tokens = set(re.findall(r"[a-z]{4,}", req.lower()))
        if any(len(tokens & set(re.findall(r"[a-z]{4,}", f.lower()))) / max(1, len(tokens | set(re.findall(r"[a-z]{4,}", f.lower())))) >= 0.6
               for f in accepted):
            continue
        accepted.append(req)
        if len(accepted) >= max_n:
            break
    return accepted, rejected


def parse_requirements(text: str, max_n: int = 4) -> List[str]:
    """Parse-only variant (no screening): 'REQUIREMENT: <statement>' lines of at least 8 words."""
    return split_requirements(text, max_n, None)[0]


def _magnitude_issue(text: str) -> Optional[str]:
    t = re.sub(r"^[\s<>\u2248~\u2264\u2265\u00b1=]+", "", (text or "").strip())
    m = _NUMBER.match(t)
    if not m:
        return "MAGNITUDE needs a number (a value or an upper bound)"
    rest = t[m.end():].strip()
    if rest and parse_dimensions(rest) is None:
        return f"MAGNITUDE units '{rest}' cannot be parsed as SI units"
    return None


def validate_candidate(cand: Candidate, allow_new_physics: bool, strategy: str = "postulate") -> Tuple[List[str], List[str]]:
    """
    Returns (issues, notes). Any issue makes the candidate invalid; notes are informational.
    New quantities are only accepted in POSTULATE attempts, and a POSTULATE attempt must contain one.
    """
    issues: List[str] = []
    notes: List[str] = []

    for label, value in (("TITLE", cand.title), ("FAMILY", cand.family)):
        if not value.strip():
            issues.append(f"missing {label}")
    if _words(cand.mechanism) < MIN_MECHANISM_WORDS:
        issues.append(f"MECHANISM missing or shorter than {MIN_MECHANISM_WORDS} words")
    hit = _SELF_REFERENCE.search(cand.mechanism)
    if hit:
        issues.append(f"MECHANISM refers to an earlier version ('{hit.group(0)}'): it must be self-contained, describe every component again")
    if _words(cand.prediction) < MIN_PREDICTION_WORDS:
        issues.append(f"PREDICTION missing or shorter than {MIN_PREDICTION_WORDS} words")
    elif not re.search(r"\d", cand.prediction):
        issues.append("PREDICTION has no number (it must be measurable)")
    if _words(cand.refutation) < MIN_PREDICTION_WORDS:
        issues.append(f"REFUTATION missing or shorter than {MIN_PREDICTION_WORDS} words")

    if cand.postulates and not (allow_new_physics and strategy == "postulate"):
        issues.append("NEW QUANTITY is only allowed in POSTULATE attempts (use known physics here)")
    if strategy == "postulate" and allow_new_physics and not cand.postulates:
        issues.append("a POSTULATE attempt must declare exactly one NEW QUANTITY line")
    if len(cand.postulates) > MAX_POSTULATES:
        issues.append(f"more than {MAX_POSTULATES} NEW QUANTITY lines (keep it parsimonious)")

    for post in cand.postulates[:MAX_POSTULATES + 1]:
        tag = post.name or "unnamed quantity"
        dims_text = post.dimensions.strip()
        if _words(post.definition) < 6:
            issues.append(f"{tag}: DEFINITION too short")
        if _words(post.coupling) < 6:
            issues.append(f"{tag}: COUPLING too short")
        if _words(post.reduces_to) < 4:
            issues.append(f"{tag}: REDUCES TO KNOWN PHYSICS WHEN too short")
        if not post.symbol.strip() or len(post.symbol.strip()) > 6:
            issues.append(f"{tag}: SYMBOL must be 1 to 6 characters")
        if len(post.equation.strip()) < 5 or "=" not in post.equation:
            issues.append(f"{tag}: EQUATION must be a real equation containing '='")
        elif post.symbol.strip() and _ascii(post.symbol.strip()) not in _ascii(post.equation):
            issues.append(f"{tag}: EQUATION must use the declared SYMBOL '{post.symbol.strip()}'")
        magnitude_issue = _magnitude_issue(post.magnitude)
        if magnitude_issue:
            issues.append(f"{tag}: {magnitude_issue}")
        if not dims_text:
            issues.append(f"{tag}: DIMENSIONS missing")
        elif "new" in dims_text.lower() and "dimension" in dims_text.lower():
            notes.append(f"{tag}: declares a NEW base dimension (cannot be dimensionally checked)")
        else:
            dim = parse_dimensions(dims_text)
            if dim is None:
                issues.append(f"{tag}: DIMENSIONS '{dims_text}' cannot be parsed as SI units")
            else:
                known = same_dimension_as(dim)
                if known:
                    if _words(post.differs_by) < 6:
                        issues.append(f"{tag}: has the dimensions of {known} (a known quantity under a new name?). "
                                      "Add 'DIFFERS FROM KNOWN QUANTITY BY: ...' (at least 6 words) or give it different dimensions")
                    else:
                        notes.append(f"{tag}: dimensions ({describe(dim)}) equal {known}; declared difference: {post.differs_by}")
    return issues, notes


def format_postulate(p: Postulate) -> str:
    text = (f"{p.name} ({p.symbol}) [{p.dimensions}]: {p.definition} | equation: {p.equation} | "
            f"magnitude: {p.magnitude} | couples via: {p.coupling} | reduces to known physics when: {p.reduces_to}")
    if p.differs_by:
        text += f" | differs from the known quantity by: {p.differs_by}"
    return text


def compose_description(cand: Candidate) -> str:
    """Clean text of the hypothesis (this is what the Critic, the red-flag screen and the PDF see)."""
    parts = [cand.title, f"Mechanism family: {cand.family}", cand.mechanism]
    for p in cand.postulates:
        parts.append(f"Postulated new quantity: {format_postulate(p)}")
    parts.append(f"Prediction: {cand.prediction}")
    parts.append(f"Refutation: {cand.refutation}")
    return "\n".join(parts)
