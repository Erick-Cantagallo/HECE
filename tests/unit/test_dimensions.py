# HECE/tests/unit/test_dimensions.py
from hece.dimensions import parse_dimensions, describe, same_dimension_as

def test_equivalent_spellings_give_the_same_dimension():
    ref = parse_dimensions("kg m^2 s^-2")
    for text in ("J", "N·m", "kg m2 s-2", "kg*m**2/s**2", "kg m² s⁻²", "eV"):
        assert parse_dimensions(text) == ref, text

def test_known_quantity_detection():
    assert same_dimension_as(parse_dimensions("J")) == "energy or torque"
    assert same_dimension_as(parse_dimensions("W/m^2")) == "intensity (power per area)"
    assert same_dimension_as(parse_dimensions("m s^-2")) == "acceleration"
    assert same_dimension_as(parse_dimensions("kg m^-3 s^4")) is None

def test_prefixes_and_division():
    assert parse_dimensions("GPa") == parse_dimensions("Pa")
    assert describe(parse_dimensions("J/(kg K)")) == "m^2 s^-2 K^-1"
    assert parse_dimensions("dimensionless") == parse_dimensions("1")

def test_garbage_is_rejected():
    for bad in ("flurbs", "kg m^", "kg (m", "??", ""):
        assert parse_dimensions(bad) is None, bad


def test_real_world_spellings_from_the_local_model():
    assert parse_dimensions("m^2 C^(-2)") == parse_dimensions("m^2 A^-2 s^-2")      # parenthesised exponent
    assert parse_dimensions("J (joules)") == parse_dimensions("J")                  # descriptive word in parentheses
    assert parse_dimensions("m^2 kg (kilograms) s^(-2)") == parse_dimensions("J")
    assert parse_dimensions("kg (m)") == parse_dimensions("kg m")                   # a real group is kept
