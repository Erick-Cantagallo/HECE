# HECE/src/hece/verification.py
import re
from typing import Any, List, Tuple

MIN_QUOTE_WORDS = 4
MIN_MECHANISM_WORDS = 15
MIN_LAW_CHARS = 8
_IGNORE = {"none", "none.", "n/a", "nil", "nothing", "empty", "no", "false", "no laws broken"}


def _norm(text: Any) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(text).lower())).strip()


def verify_violation(claim: Any, hypothesis_text: str, hard_constraints: List[str]) -> bool:
    """
    A violation claim is accepted only if it is provable:
    - 'law' matches one of the known hard constraints,
    - 'quote' really appears in the hypothesis text,
    - 'mechanism' is a real explanation (minimum length).
    Does NOT judge whether the physics reasoning is correct.
    """
    if not isinstance(claim, dict):
        return False
    law = _norm(claim.get("law", ""))
    quote = _norm(claim.get("quote", ""))
    mechanism = str(claim.get("mechanism", ""))
    if len(law) < MIN_LAW_CHARS or len(quote.split()) < MIN_QUOTE_WORDS:
        return False
    if len(mechanism.split()) < MIN_MECHANISM_WORDS:
        return False
    if not any(law in _norm(h) for h in hard_constraints):
        return False
    return quote in _norm(hypothesis_text)


def split_violations(raw: Any, hypothesis_text: str, hard_constraints: List[str]) -> Tuple[List[str], List[str]]:
    """Returns (verified_laws, unverified_claims) from the LLM's raw violation list."""
    if isinstance(raw, (dict, str)):
        raw = [raw]
    elif not isinstance(raw, list):
        raw = []

    verified: List[str] = []
    unverified: List[str] = []
    for item in raw:
        if isinstance(item, str) and item.strip().lower() in _IGNORE:
            continue
        if verify_violation(item, hypothesis_text, hard_constraints):
            verified.append(str(item["law"]).strip())
        elif isinstance(item, dict):
            unverified.append(str(item.get("law", "unknown law")).strip() or "unknown law")
        elif str(item).strip():
            unverified.append(str(item).strip())
    return verified, unverified


def filter_citations(citations: List[str], source_text: str) -> List[str]:
    """
    Keeps only citations that match a paper actually retrieved (listed in source_text as
    '- Title: ...' followed by 'ID: ...'). Returns canonical 'Title (arXiv:ID)' strings.
    Anything the LLM invented (titles or arXiv IDs never retrieved) is dropped.
    """
    papers = re.findall(r"^- (?:\[\d+\]\s*)?Title: (.+)\n\s*ID: (\S+)", source_text or "", flags=re.M)
    kept: List[str] = []
    for cit in citations:
        c = _norm(cit)
        if not c:
            continue
        for title, pid in papers:
            t = _norm(title)
            matches = (t and t in c) or (pid.lower() in str(cit).lower()) \
                or (len(c.split()) >= 4 and c in t)
            if matches:
                canonical = f"{title} (arXiv:{pid})"
                if canonical not in kept:
                    kept.append(canonical)
                break
    return kept


def verified_evidence(raw: Any, hypothesis_text: str, hard_constraints: List[str]) -> List[str]:
    """Human-readable proof (law, quote, mechanism) for every claim that passed verification."""
    if isinstance(raw, dict):
        raw = [raw]
    elif not isinstance(raw, list):
        return []
    return [
        f'{str(c["law"]).strip()} | quote: "{str(c["quote"]).strip()}" | mechanism: {str(c["mechanism"]).strip()}'
        for c in raw if verify_violation(c, hypothesis_text, hard_constraints)
    ]


_FLAW_LINE = re.compile(r"^\s*(?:[-*\u2022]|\d+[.)])?\s*FLAW\s*:\s*(.+?)\s*\|\s*QUOTE\s*:\s*(.+?)\s*$", re.I)


def parse_flaws(review_text: str, hypothesis_text: str, max_flaws: int = 5) -> List[str]:
    """
    Parses lines 'FLAW: <sentence> | QUOTE: <words copied from the hypothesis>'.
    A flaw counts only if its quote really appears in the hypothesis (grounded), so an
    eager Critic cannot invent problems out of thin air.
    """
    flaws: List[str] = []
    for line in str(review_text).splitlines():
        m = _FLAW_LINE.match(line)
        if not m:
            continue
        flaw, quote = m.group(1).strip(), m.group(2).strip().strip("\"'\u201c\u201d")
        q = _norm(quote)
        if len(flaw.split()) >= 4 and len(q.split()) >= MIN_QUOTE_WORDS and q in _norm(hypothesis_text):
            item = f"{flaw} (quote: '{quote}')"
            if item not in flaws:
                flaws.append(item)
        if len(flaws) >= max_flaws:
            break
    return flaws


def resolve_numbered_refs(text: str, source_text: str) -> List[str]:
    """Maps '[n]' references in a hypothesis to the n-th retrieved paper (numbering shown to the LLM)."""
    by_num = {int(n): (t, i) for n, t, i in
              re.findall(r"^- \[(\d+)\] Title: (.+)\n\s*ID: (\S+)", source_text or "", flags=re.M)}
    out: List[str] = []
    for n in re.findall(r"\[(\d+)\]", text or ""):
        paper = by_num.get(int(n))
        if paper:
            canonical = f"{paper[0]} (arXiv:{paper[1]})"
            if canonical not in out:
                out.append(canonical)
    return out


_GOAL_STOP = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are", "can", "be", "by", "with",
              "via", "novel", "new", "approach", "method", "using", "use", "this", "that"}


def _tokens(text: str) -> set:
    return {w for w in _norm(text).split() if w not in _GOAL_STOP and len(w) > 2}


def drop_goal_restatements(items: List[str], goal_text: str, threshold: float = 0.6) -> List[str]:
    """An 'assumption' that merely restates the goal is the claim itself, not an extra unproven premise."""
    goal = _tokens(goal_text)
    kept: List[str] = []
    for item in items:
        t = _tokens(item)
        if len(t) >= 3 and len(t & goal) / len(t) >= threshold:
            continue
        kept.append(item)
    return kept


_LAW_WORDS = re.compile(
    r"first law|second law|third law|thermodynamic|speed of light|conservation of|entropy increases|"
    r"energy cannot|carnot|violat\w+ (?:the )?(?:known )?laws?", re.I)


def split_law_flaws(flaws: List[str]) -> Tuple[List[str], List[str]]:
    """
    A 'flaw' that accuses the hypothesis of breaking a physical law is really a law accusation.
    It must not slip past the law verification, so it is separated here: (plain_flaws, law_flaws).
    """
    plain: List[str] = []
    law: List[str] = []
    for flaw in flaws:
        (law if _LAW_WORDS.search(flaw.split(" (quote:")[0]) else plain).append(flaw)
    return plain, law
