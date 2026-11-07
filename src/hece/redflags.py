# HECE/src/hece/redflags.py
"""
Deterministic screen for well-known pseudo-scientific patterns in a hypothesis text.
It is a HEURISTIC list: it catches known red flags, not arbitrary errors. Extend it as needed.
A pattern is ignored when it appears right after a negation (e.g. "without exotic matter").
"""
import re
from typing import List

_PATTERNS = [
    ("entropy claimed constant (reversible / zero entropy production)",
     r"entropy[^.]{0,40}\b(?:remains?|stays?|is kept|kept)\s+constant"),
    ("perpetual motion / over-unity / free energy",
     r"perpetual|over-?unity|(?:unlimited|infinite|limitless)\s+(?:free\s+)?energy"
     r"|free[- ]energy\s+(?:device|generator|machine)|energy from nothing|self-sustaining (?:energy )?loop"),
    ("100% efficiency or zero losses",
     r"100\s?%\s*efficien\w+|\b(?:zero|no)\s+(?:energy\s+)?loss(?:es)?\b"),
    ("faster-than-light travel or signalling",
     r"faster[- ]than[- ]light|superluminal|\bFTL\b"),
    ("exotic matter / negative energy or mass",
     r"exotic matter|negative (?:mass|energy)"),
    ("entanglement used as energy storage or transfer",
     r"entangle\w*[^.]{0,30}\b(?:energy|power)\s+(?:storage|transfer|transmission|battery)"
     r"|energy[- ]storage[^.]{0,30}entangle\w*"),
    ("entropy reversal or negative entropy claim",
     r"negative entropy|reversal of (?:the )?entropy|entropy reversal|reverses? (?:the )?(?:flow of )?entropy"),
    ("sound or pressure wave propagating through vacuum (needs a medium)",
     r"(?:sonic|acoustic|ultrasonic|ultrasound|sound|mach|shock|pressure)[^.]{0,80}\b(?:through|across|via)\s+(?:the\s+)?"
     r"(?:vacuum of space|empty space|outer space|interstellar space|vacuum)\b(?!\s+(?:chamber|tube|cavity|pump|system|fluctuation|energy))"),
    ("relies on a hypothetical or undiscovered ingredient as if it were available (making it is the hard part)",
     r"(?:shell|layer|core|slab|sheet|ring|sphere|region|block|plate|membrane|source|reservoir|bubble)s? of "
     r"(?:exotic matter|negative[- ]mass|tachyons?|magnetic monopoles?)"
     r"|(?:using|uses|use|with|made of|composed of|assum\w+|place\w*|embed\w*|insert\w*|load\w*)\s+(?:an?\s+|the\s+|some\s+)?"
     r"(?:\w+\s+){0,3}(?:exotic matter|negative[- ]mass|tachyons?|magnetic monopoles?)"),
    ("needs an astronomical object as part of the apparatus",
     r"(?:place|placing|placed|embed\w*|insert\w*|install\w*|build|built)\b.{0,90}\b(?:neutron stars?|black holes?|white dwarfs?|pulsars?)\b"),
    ("extracting vacuum / zero-point energy",
     r"(?:tap|extract|harvest|borrow)\w*[^.]{0,60}\b(?:vacuum|zero[- ]point)\b[^.]{0,20}(?:energy|fluctuations)"
     r"|(?:recharg|charg|power|energi)\w*[^.]{0,30}\bfrom the (?:quantum )?vacuum\b"
     r"|\b(?:work|energy|power)\s+(?:output\s+)?(?:[\w-]+\s+){0,2}from (?:the )?(?:quantum )?vacuum\b"),
    ("water memory / structured water",
     r"structured water|\bwater\b[^.]{0,40}\b(?:memory|remembers?)\b"),
    # Not law-level: changing the assumptions behind a limit is a legitimate creative path (e.g. tandem solar cells).
    ("claims to beat a theoretical or thermodynamic limit",
     r"(?:below|under|beat\w*|exceed\w*|surpass\w*|break\w*)\s+(?:the\s+)?(?:theoretical|thermodynamic|Carnot|Betz|Landauer)"
     r"\s+(?:minimum|limit|maximum|bound)"),
]

# Output or work claimed with no ENERGY input at all. Passive devices that run without electricity or fuel
# (solar, radiative cooling) are legitimate, so only 'energy' counts here. These phrases ARE negations, so the
# negation filter must not apply.
_NO_ENERGY_INPUT = re.compile(
    r"\b(?:no|without(?:\s+any)?|zero)\s+(?:external\s+)?energy\s+(?:input|supply|source)\b"
    r"|\b(?:needs?|requires?)\s+no\s+(?:external\s+)?energy\b"
    r"|\bself-running\b|\bkeeps?\s+accelerating\b|\bfree\s+(?:electricity|power)\b", re.I)  # not 'free energy': Gibbs/Helmholtz free energy is physics
_PERPETUAL = "perpetual motion / over-unity / free energy"

# Categories that, if true, contradict a fundamental law. They are text heuristics, so they do not zero the score,
# but they block acceptance: a human has to look (SimulationEngine.evaluate).
LAW_LEVEL = (_PERPETUAL, "faster-than-light travel or signalling", "entropy reversal or negative entropy claim",
             "extracting vacuum / zero-point energy")
_NEGATION = re.compile(r"\b(?:no|not|without|never|neither|nor|avoids?|eliminat\w+|instead of|rather than|unlike|"
                       r"as opposed to)\b|n't", re.I)


def find_red_flags(text: str, speculative: bool = False) -> List[str]:
    """
    Returns one entry per matched category: 'category: snippet'.
    In speculative (inventor) mode, exotic matter / negative energy is a legitimate thing to explore,
    so that category is not penalised.
    """
    flags: List[str] = []
    for name, pattern in _PATTERNS:
        if speculative and name.startswith("exotic matter"):
            continue
        if not speculative and name.startswith("relies on a hypothetical"):
            continue   # classic mode already penalises exotic matter in general; avoid counting it twice
        for m in re.finditer(pattern, text or "", flags=re.I):
            if _NEGATION.search(text[max(0, m.start() - 30):m.start()]):
                continue
            snippet = " ".join(m.group(0).split())[:80]
            flags.append(f"{name}: '{snippet}'")
            break
    if not any(f.startswith(_PERPETUAL) for f in flags):
        m = _NO_ENERGY_INPUT.search(text or "")
        if m:
            flags.append(f"{_PERPETUAL}: '{' '.join(m.group(0).split())[:80]}'")
    flags.extend(_extraordinary_energy_claims(text or ""))
    flags.extend(_vague_wording(text or ""))
    return flags


_FACTOR = re.compile(r"\bfactor of (\d+(?:\.\d+)?)(?:\s*(?:-|\u2013|to)\s*(\d+(?:\.\d+)?))?", re.I)
_PERCENT = re.compile(r"\b(\d{2,3})\s?%\s+(?:reduction|decrease|saving|savings)", re.I)
_REDUCTION_WORD = re.compile(r"reduc|lower|decreas|cut|sav", re.I)
_ENERGY_WORD = re.compile(r"energy|power|consumption", re.I)


def _extraordinary_energy_claims(text: str) -> List[str]:
    """Energy-reduction claims of a factor >= 10 (or >= 90%) are extraordinary and need a cited source."""
    found: List[str] = []
    for m in _FACTOR.finditer(text):
        before = text[max(0, m.start() - 100):m.start()]
        value = max(float(g) for g in m.groups() if g)
        if value >= 10 and _REDUCTION_WORD.search(before) and _ENERGY_WORD.search(before) \
                and not _NEGATION.search(before[-30:]):
            found.append(f"extraordinary energy-reduction claim (factor >= 10 needs a cited source): '{' '.join(m.group(0).split())}'")
            break
    if not found:
        for m in _PERCENT.finditer(text):
            around = text[max(0, m.start() - 100):m.end() + 60]
            if int(m.group(1)) >= 90 and _ENERGY_WORD.search(around):
                found.append(f"extraordinary energy-reduction claim (>= 90% needs a cited source): '{' '.join(m.group(0).split())}'")
                break
    return found


_VAGUE = re.compile(
    r"\bor other means\b|\bor similar\b|\bor something\b|\band so on\b|\betc\b\.?|\bin some way\b|\bby some means\b|"
    r"\bany (?:significant|noticeable|measurable|detectable) (?:\w+ ){0,2}(?:effects?|changes?|signals?|differences?)\b", re.I)


def _vague_wording(text: str) -> List[str]:
    """A prediction or refutation worded like 'or other means' or 'any significant effect' cannot be falsified."""
    m = re.search(r"\bPrediction:(.*)$", text, flags=re.S)
    if not m:
        return []
    hit = _VAGUE.search(m.group(1))
    return [f"vague prediction/refutation wording (not falsifiable as written): '{' '.join(hit.group(0).split())}'"] if hit else []


def law_level_flags(flags: List[str]) -> List[str]:
    """The red flags whose category contradicts a fundamental law (see LAW_LEVEL)."""
    return [f for f in flags if f.startswith(LAW_LEVEL)]
