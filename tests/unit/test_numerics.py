# HECE/tests/unit/test_numerics.py
from hece.numerics import find_numeric_inconsistencies as check, unit_si, find_scale_mismatch

REAL_WRONG = [
    "emitting a speed of less than or equal to 300 meters per second (m/s), which is 0.01c.",
    "less than or equal to 450 meters per second (m/s), which is 0.015c",
    "a speed greater than 600 m/s (0.02c)",
]
FINE = [
    "emitting a precisely tuned 30 kHz frequency wave (30,000 Hz, 17.5 meters per second)",
    "approximately 0.01 times the speed of light (0.01c)",
    "3e6 m/s, which is 0.01c",
    "a 10 cm tube (2 mm thick)",                         # parentheses often add a DIFFERENT quantity
    "10 \u00b5m, i.e. 0.01 mm", "100 kV pulse, about 1e5 V", "1 eV = 1.6e-19 J", "a pressure of 1 bar (100 kPa) was used",
    "5 J, which is 5 W",                                 # different dimensions are never compared
]

def test_arithmetic_errors_from_real_runs_are_found():
    for text in REAL_WRONG:
        found = check(text)
        assert len(found) == 1 and "differ" in found[0], text

def test_consistent_or_unrelated_numbers_are_left_alone():
    for text in FINE:
        assert check(text) == [], text

def test_other_unit_families_are_converted_correctly():
    assert len(check("10 um, i.e. 0.5 mm")) == 1 and len(check("1 eV = 3 J")) == 1
    assert check("2 GHz, which is 2000 MHz") == [] and len(check("2 GHz, which is 200 MHz")) == 1

def test_unit_conversion_table():
    dim, scale = unit_si("km/s")
    assert scale == 1000.0 and dim == unit_si("m/s")[0]
    assert unit_si("flurbs") is None and unit_si("a/b/c") is None


REAL_MISMATCH = ("Orders of magnitude: * Phononic crystal plate thickness: 1-10 \u03bcm * Cavity resonator size: 1-10 \u03bcm "
                 "* quality factor (Q) of at least 10^5\nPrediction: a density below -1e-6 J/m^3 within a 1 cm\u00b3 volume for 1 ms.")

def test_a_region_far_larger_than_every_component_is_flagged():
    found = find_scale_mismatch(REAL_MISMATCH)               # unicode micro sign and cm\u00b3, as the model writes them
    assert len(found) == 1 and "1000x smaller" in found[0]
    assert len(find_scale_mismatch("A resonator 10 \u00b5m wide.\nPrediction: a signal over a 1 cubic centimetre volume.")) == 1

def test_matching_scales_arrays_and_missing_sizes_are_left_alone():
    assert find_scale_mismatch("A device 5 cm wide with a 2 cm gap.\nPrediction: a field of 3 mT in a 1 cm^3 volume.") == []
    assert find_scale_mismatch("An array of 10 \u00b5m cells tiles the plate.\nPrediction: a signal in a 1 cm^3 volume.") == []
    assert find_scale_mismatch("A resonator is built.\nPrediction: a signal in a 1 cm^3 volume.") == []     # no sizes stated
    assert find_scale_mismatch("A resonator 10 \u00b5m wide.\nPrediction: a signal.") == []                   # no volume claimed
    assert find_scale_mismatch("A resonator 10 \u00b5m wide with Q of at least 10^5.\nPrediction: signal in 1 mm^3.") == []  # 1 mm / 10 um = 100
