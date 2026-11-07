# HECE/tests/unit/test_concepts.py
import random
from hece.concepts import sample_concepts, concept_category, CONCEPT_BANK

def test_sampling_is_reproducible_and_cross_category():
    a = sample_concepts(random.Random(7), 3, "")
    b = sample_concepts(random.Random(7), 3, "")
    assert a == b and len(a) == 3
    assert len({concept_category(c) for c in a}) == 3

def test_concepts_already_in_the_goal_are_skipped():
    for seed in range(30):
        for c in sample_concepts(random.Random(seed), 5, "desalination with vacuum and resonance"):
            assert c not in ("ultra-high vacuum", "resonance")

def test_bank_has_no_duplicates():
    allc = [c for items in CONCEPT_BANK.values() for c in items]
    assert len(allc) == len(set(allc))
