# HECE/tests/unit/test_redflags.py
from hece.redflags import find_red_flags

H1 = ("The EEM consists of a thermally-coupled membrane unit and a quantum-entangled energy storage system. "
      "The EEM relies on the Second Law to ensure that the entropy of the system remains constant.")
H2 = ("The Second Law of Thermodynamics is directly applicable here, as the increase in entropy due to the localized "
      "electromagnetic field will be compensated by the decrease in entropy resulting from the reduced energy consumption.")

def test_flags_entropy_constant_and_entangled_storage():
    flags = find_red_flags(H1)
    assert len(flags) == 2
    assert any("entropy claimed constant" in f for f in flags)
    assert any("entanglement used as energy storage" in f for f in flags)

def test_clean_text_has_no_flags():
    assert find_red_flags(H2) == []

def test_negated_mention_is_ignored():
    assert find_red_flags("The design works without exotic matter and avoids faster-than-light claims.") == []

def test_asserted_pattern_is_flagged_once_per_category():
    assert len(find_red_flags("It needs exotic matter. Exotic matter with negative mass stabilizes it.")) == 1

def test_gibbs_free_energy_is_not_a_red_flag():
    assert find_red_flags("The reduction in the Gibbs free energy enables the separation at lower cost.") == []

H3 = ("The quantum flux is harnessed to operate in a region of negative entropy. It allows the process to tap into the "
      "quantum fluctuations in the vacuum energy, and the temporary local reversal of entropy reduces the cost.")

def test_entropy_reversal_and_vacuum_tapping_are_flagged():
    flags = find_red_flags(H3)
    assert len(flags) == 2
    assert any("entropy reversal" in f for f in flags) and any("vacuum" in f for f in flags)

def test_extraordinary_energy_claim_is_flagged():
    text = "this device could potentially reduce the energy consumption of seawater desalination by a factor of 10-20, compared to current methods."
    flags = find_red_flags(text)
    assert len(flags) == 1 and "extraordinary energy-reduction claim" in flags[0]

def test_modest_or_unrelated_factors_are_not_flagged():
    assert find_red_flags("It reduces the energy consumption by a factor of 2 compared to the baseline.") == []
    assert find_red_flags("Permeability improves by a factor of 100 as reported in the literature.") == []
    assert find_red_flags("It reduces energy use by 30% on average.") == []

def test_ninety_percent_energy_reduction_is_flagged():
    assert len(find_red_flags("The design gives a 95% reduction in energy consumption.")) == 1

def test_speculative_flag_only_skips_exotic_matter():
    text = "It needs exotic matter and also claims faster-than-light travel."
    assert len(find_red_flags(text)) == 2
    flags = find_red_flags(text, speculative=True)
    assert len(flags) == 1 and "faster-than-light" in flags[0]


def test_sound_cannot_travel_through_vacuum():
    real = "The Sonic Tunneling Gun uses a carefully controlled sonic boom to create a temporary tunnel through the vacuum of space."
    flags = find_red_flags(real)
    assert len(flags) == 1 and "needs a medium" in flags[0]
    assert find_red_flags("A sonic beam is focused onto a membrane at the edge of a vacuum chamber evacuated to 1e-3 mbar.") == []
    assert find_red_flags("An acoustic wave travels through the vacuum chamber walls into the sample.") == []


REAL_ACTIVE = ("The mechanism creates a localized region with negative energy density. This is achieved by carefully designing a "
               "spherical shell of negative mass, approximately 1 cm in radius, and placing it at the center of a dense, massive object "
               "(e.g., a neutron star or a black hole).\n"
               "Prediction: The sustained negative energy density of -1e-6 J/m^3 in the 1 cm^3 pocket, detectable through gravitational "
               "lensing effects or other means, within at least 1 ms.\n"
               "Refutation: A positive energy density value in the pocket, or a failure to detect any significant gravitational lensing effects.")

def test_the_first_real_active_candidate_is_now_caught_three_ways():
    flags = find_red_flags(REAL_ACTIVE, speculative=True)
    kinds = " | ".join(flags)
    assert len(flags) == 3
    assert "hypothetical or undiscovered ingredient" in kinds and "astronomical object" in kinds and "vague prediction" in kinds

def test_producing_negative_energy_by_known_physics_is_not_flagged():
    text = ("Two parallel conducting plates 5 micrometres apart create a region of negative energy density through the Casimir effect.\n"
            "Prediction: A force of 1e-4 N per square metre between the plates is measured at a 5 micrometre gap.\n"
            "Refutation: A measured force below 1e-5 N per square metre at that gap would refute the idea.")
    assert find_red_flags(text, speculative=True) == []

def test_negated_or_observational_mentions_are_ignored():
    assert find_red_flags("The design works without a shell of negative mass.", speculative=True) == []
    assert find_red_flags("Telescopes observe light bent near a black hole to calibrate the instrument.", speculative=True) == []
    assert len(find_red_flags("Prediction: a signal of 3 mV is measured, or other means may be used.")) == 1
    assert find_red_flags("A signal of 3 mV, or other means, appears.") == []        # only the Prediction/Refutation part is checked


def test_energy_without_input_is_a_law_level_flag():
    from hece.redflags import law_level_flags
    flags = find_red_flags("Once started, the self-running rotor drives a generator with no external energy input.")
    assert law_level_flags(flags)


def test_passive_devices_and_negated_mentions_are_not_law_level():
    from hece.redflags import law_level_flags
    for text in ["Passive radiative cooling panels need no electricity: they emit infrared to the cold sky.",
                 "A passive solar distiller works without any electricity or pumps, driven only by sunlight.",
                 "Unlike perpetual motion machines, this flywheel loses energy to friction and must be recharged.",
                 "A self-powered sensor harvests vibration energy from the bridge it monitors."]:
        assert law_level_flags(find_red_flags(text)) == [], text


def test_law_level_flag_blocks_acceptance_even_with_a_high_score():
    from hece.core.models.base import ConstraintContext, Hypothesis
    from hece.simulation import SimulationEngine
    text = "The self-running magnet motor powers the house." + " It is built from standard parts and magnets." * 10
    hyp = Hypothesis(id="h", goal_id="g", description=text, feasibility_score=0.95)

    [result] = SimulationEngine().evaluate([hyp], ConstraintContext(goal_id="g"))

    assert result.feasibility_score == 0.8  # one red flag: -15%, still above the threshold...
    assert result.status == "rejected" and result.needs_human_review  # ...but it is blocked
    assert SimulationEngine().rejection_reason(result).startswith("Blocked for human review")
