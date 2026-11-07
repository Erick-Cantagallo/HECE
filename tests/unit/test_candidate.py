# HECE/tests/unit/test_candidate.py
from hece.candidate import (parse_candidate, validate_candidate, compose_description, parse_requirements,
                            screen_requirement, split_requirements)

MECH = ("The membrane couples a thermal gradient of about 20 K to a strain wave in the lattice. " * 5).strip()
GOOD = f"""TITLE: Strain-wave desalting membrane
FAMILY: strain wave pumping
MECHANISM: {MECH}
PREDICTION: Water flux of 12 litres per square metre per hour at 20 K gradient and 1 bar.
REFUTATION: A flux below 1 litre per square metre per hour at the same gradient would refute the idea.
"""
QUANTITY = ("NEW QUANTITY: lattice torsion charge | SYMBOL: Qt | DIMENSIONS: kg m^3 s^-1 | DEFINITION: a conserved count of "
            "lattice twist per unit length | EQUATION: dQt/dt = k * E * B | MAGNITUDE: < 1e-12 m^3 s^-2 | COUPLING: it couples "
            "to phonon momentum through a dimensionless constant | REDUCES TO KNOWN PHYSICS WHEN: the coupling constant tends to zero\n")


def issues_of(text, allow=True, strategy="postulate"):
    return validate_candidate(parse_candidate(text), allow, strategy)[0]


def test_valid_candidate_parses_without_issues():
    c = parse_candidate("Sure! Here you go:\n**" + GOOD.replace("\n", "**\n**", 1))
    assert c.title and c.family
    assert issues_of(GOOD, allow=False, strategy="explore") == []

def test_missing_sections_and_non_numeric_prediction_are_issues():
    c = parse_candidate("TITLE: x\nFAMILY: y\nMECHANISM: too short\nPREDICTION: it will work very well in practice for sure\nREFUTATION: n")
    joined = " ".join(validate_candidate(c, False, "explore")[0])
    assert "MECHANISM" in joined and "no number" in joined and "REFUTATION" in joined

def test_new_quantity_only_in_postulate_attempts_and_required_there():
    with_q = GOOD + QUANTITY
    assert issues_of(with_q, True, "postulate") == []
    assert any("only allowed in POSTULATE" in i for i in issues_of(with_q, True, "explore"))
    assert any("only allowed in POSTULATE" in i for i in issues_of(with_q, False, "postulate"))
    assert any("must declare exactly one NEW QUANTITY" in i for i in issues_of(GOOD, True, "postulate"))

def test_postulate_must_be_a_real_equation_with_a_magnitude():
    assert any("EQUATION must be a real equation" in i for i in issues_of(GOOD + QUANTITY.replace("dQt/dt = k * E * B", "grows with the field")))
    assert any("declared SYMBOL" in i for i in issues_of(GOOD + QUANTITY.replace("dQt/dt = k * E * B", "dX/dt = k * E")))
    assert any("needs a number" in i for i in issues_of(GOOD + QUANTITY.replace("< 1e-12 m^3 s^-2", "very small")))
    assert any("cannot be parsed" in i for i in issues_of(GOOD + QUANTITY.replace("m^3 s^-2", "flurbs")))
    assert issues_of(GOOD + QUANTITY.replace("< 1e-12 m^3 s^-2", "10^-3 m^3 s^-2")) == []

def test_invalid_dimensions_are_rejected_but_real_world_spellings_are_accepted():
    assert any("DIMENSIONS" in i and "cannot be parsed" in i for i in issues_of(GOOD + QUANTITY.replace("kg m^3 s^-1", "flurbs per second")))
    assert issues_of(GOOD + QUANTITY.replace("kg m^3 s^-1", "m^3 kg (kilograms) s^(-1)")) == []

def test_renamed_known_quantity_is_rejected_unless_the_difference_is_explained():
    renamed = GOOD + QUANTITY.replace("kg m^3 s^-1", "J")
    assert any("known quantity under a new name" in i for i in issues_of(renamed))
    explained = renamed.rstrip("\n") + " | DIFFERS FROM KNOWN QUANTITY BY: it is stored only in torsional lattice modes and never thermalises\n"
    issues, notes = validate_candidate(parse_candidate(explained), True, "postulate")
    assert issues == [] and any("energy or torque" in n for n in notes)

def test_too_many_postulates_and_incomplete_postulate():
    assert any("more than 2" in i for i in issues_of(GOOD + QUANTITY * 3))
    short = GOOD + "NEW QUANTITY: q | SYMBOL: q | DIMENSIONS: kg m^3 | DEFINITION: tiny | EQUATION: q = 1 | MAGNITUDE: 1 | COUPLING: x | REDUCES TO KNOWN PHYSICS WHEN: y"
    assert any("too short" in i for i in issues_of(short))

def test_none_postulate_is_ignored_and_description_is_clean():
    c = parse_candidate("Great idea!\n" + GOOD + "NEW QUANTITY: none\n")
    assert c.postulates == []
    text = compose_description(c)
    assert text.startswith("Strain-wave desalting membrane") and "Great idea" not in text
    assert "Prediction:" in text and "Refutation:" in text

def test_description_shows_equation_and_magnitude_of_a_postulate():
    text = compose_description(parse_candidate(GOOD + QUANTITY))
    assert "equation: dQt/dt = k * E * B" in text and "magnitude: < 1e-12 m^3 s^-2" in text

def test_parse_requirements_keeps_distinct_measurable_lines():
    raw = ("Sure, here they are:\n"
           "REQUIREMENT: Sustain a negative energy density of at least 1e-6 J per cubic metre in a one cubic centimetre volume\n"
           "- REQUIREMENT: Sustain a negative energy density of at least 1e-6 J per cubic metre inside one cubic centimetre volume\n"
           "2. REQUIREMENT: Keep the throat of the structure open for at least one millisecond against collapse\n"
           "REQUIREMENT: too short\n")
    reqs = parse_requirements(raw)
    assert len(reqs) == 2 and reqs[1].startswith("Keep the throat")


def test_requirements_must_have_a_number_and_not_be_limits_or_laws():
    assert screen_requirement("The entropy of the portal must be lower than the entropy of the surrounding space in J/K") == "no numeric target"
    assert "limit that must not be broken" in screen_requirement(
        "The speed of the particles must be less than or equal to the speed of light in a vacuum, below 3e8 m/s")
    laws = ["MUST NOT VIOLATE: Conservation of mass and energy"]
    assert "restates a law" in screen_requirement("Conservation of mass and energy must always hold, with at most 1 percent error", laws)
    assert screen_requirement("Sustain a negative energy density of at least 1e-6 J/m^3 in a 1 cm^3 volume for 1 ms", laws) is None

def test_split_requirements_reports_why_each_line_was_rejected():
    raw = ("REQUIREMENT: The energy density of the portal must be greater than or equal to the energy density of the surrounding space\n"
           "REQUIREMENT: Hold a region of negative energy density below 1e-6 J/m^3 for at least 1 ms in a small volume\n")
    accepted, rejected = split_requirements(raw, 4, [])
    assert len(accepted) == 1 and rejected[0][1] == "no numeric target"

def test_greek_and_latin_spellings_of_a_symbol_are_the_same_symbol():
    greek = GOOD + QUANTITY.replace("SYMBOL: Qt", "SYMBOL: \u03c6").replace("dQt/dt", "dphi/dt")
    assert issues_of(greek) == []


def test_a_candidate_that_refers_to_an_earlier_version_is_invalid():
    for phrase in ("The phononic plate remains unchanged, with the same dimensions and materials as before.",
                   "The refined design maintains the core idea of the earlier candidate.",
                   "This is an improved version of the previous design."):
        text = GOOD.replace("MECHANISM: ", f"MECHANISM: {phrase} ")
        assert any("refers to an earlier version" in i for i in issues_of(text, allow=False, strategy="explore")), phrase
    assert issues_of(GOOD, allow=False, strategy="explore") == []
