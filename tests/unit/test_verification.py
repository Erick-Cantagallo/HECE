# HECE/tests/unit/test_verification.py
from hece.verification import verify_violation, split_violations, filter_citations, verified_evidence, parse_flaws, resolve_numbered_refs, drop_goal_restatements, split_law_flaws

HARD = ["MUST NOT VIOLATE: First Law of Thermodynamics (Energy cannot be created or destroyed)",
        "MUST NOT VIOLATE: Pauli exclusion principle"]
TEXT = "The device creates energy from nothing by looping the output back into the input."
MECH = "The device outputs more energy than it receives, which means energy is being created, contradicting conservation."
GOOD = {"law": "First Law of Thermodynamics", "quote": "creates energy from nothing", "mechanism": MECH}

def test_valid_claim_accepted():
    assert verify_violation(GOOD, TEXT, HARD)

def test_fake_quote_rejected():
    assert not verify_violation({**GOOD, "quote": "desalination breaks pauli exclusion"}, TEXT, HARD)

def test_unknown_law_rejected():
    assert not verify_violation({**GOOD, "law": "Law of Gravity Fantasy"}, TEXT, HARD)

def test_short_mechanism_rejected():
    assert not verify_violation({**GOOD, "mechanism": "short"}, TEXT, HARD)

def test_legacy_string_is_unverified():
    verified, unverified = split_violations(["Pauli exclusion principle"], TEXT, HARD)
    assert verified == [] and unverified == ["Pauli exclusion principle"]

def test_empty_and_none_like_values():
    assert split_violations([], TEXT, HARD) == ([], [])
    assert split_violations("N/A", TEXT, HARD) == ([], [])
    assert split_violations(None, TEXT, HARD) == ([], [])

SOURCE = "REAL SCIENTIFIC LITERATURE RETRIEVED:\n\n- Title: The Higgs Portal and Cosmology\n  ID: 1412.4743\n  Summary: x\n"

def test_filter_citations_keeps_real_and_drops_invented():
    cits = ["The Higgs Portal and Cosmology", "Fake paper (arXiv:2012.12345)", "Something arXiv:1412.4743"]
    assert filter_citations(cits, SOURCE) == ["The Higgs Portal and Cosmology (arXiv:1412.4743)"]

def test_filter_citations_without_sources_returns_empty():
    assert filter_citations(["Anything"], "KNOWN FACTS: none") == []

def test_verified_evidence_contains_quote_and_mechanism():
    ev = verified_evidence([GOOD, {**GOOD, "quote": "not in the text at all"}], TEXT, HARD)
    assert len(ev) == 1 and "creates energy from nothing" in ev[0] and "First Law of Thermodynamics" in ev[0]

FLAW_TEXT = "The device keeps entropy constant yet claims a net gain of free work from the same cycle."

def test_parse_flaws_keeps_grounded_and_drops_invented():
    review = ("1. FLAW: Entropy cannot stay constant while producing net work | QUOTE: keeps entropy constant yet claims\n"
              "- FLAW: Invented problem not in the text at all | QUOTE: totally absent words in this hypothesis\n"
              "random line without the format")
    out = parse_flaws(review, FLAW_TEXT)
    assert len(out) == 1 and "keeps entropy constant yet claims" in out[0]

def test_parse_flaws_no_flaws_and_short_quote():
    assert parse_flaws("NO FLAWS", FLAW_TEXT) == []
    assert parse_flaws("FLAW: Something is wrong here today | QUOTE: entropy constant", FLAW_TEXT) == []

NUMBERED = ("REAL SCIENTIFIC LITERATURE RETRIEVED:\n\n- [1] Title: Passive solar distiller\n  ID: 1702.05422\n  Summary: x\n"
            "\n- [2] Title: Nanoporous Carbon Nitride\n  ID: 1512.07101\n  Summary: y\n")

def test_numbered_refs_are_resolved_and_unknown_ignored():
    out = resolve_numbered_refs("as reported in [2] and also [7]", NUMBERED)
    assert out == ["Nanoporous Carbon Nitride (arXiv:1512.07101)"]

def test_filter_citations_accepts_numbered_source_format():
    assert filter_citations(["Nanoporous Carbon Nitride"], NUMBERED) == ["Nanoporous Carbon Nitride (arXiv:1512.07101)"]

GOAL = "reduce the energy consumption of seawater desalination"

def test_goal_restatement_is_not_an_assumption():
    items = ["Novel approach to reduce energy consumption in seawater desalination", "Thermally programmable membrane"]
    assert drop_goal_restatements(items, GOAL) == ["Thermally programmable membrane"]


def test_flaws_that_accuse_a_physical_law_are_separated():
    flaws = ["The step is asserted without any physical explanation (quote: 'a b c d')",
             "The prediction contradicts the Second Law of Thermodynamics (quote: 'a b c d')",
             "This violates the speed of light limit (quote: 'a b c d')"]
    plain, law = split_law_flaws(flaws)
    assert len(plain) == 1 and len(law) == 2
    assert split_law_flaws(["Nothing about laws here at all (quote: 'thermodynamic bubble claim x')"])[0]   # quote text is ignored
