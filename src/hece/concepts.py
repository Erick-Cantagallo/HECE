# HECE/src/hece/concepts.py
"""
Bank of real-world concepts used to force unusual combinations ("recombination").
Entries are only LABELS: the bank makes no scientific claim about any of them.
"""
import random
import re
from typing import Dict, List, Optional

CONCEPT_BANK: Dict[str, List[str]] = {
    "material": [
        "graphene aerogel", "metal-organic framework", "liquid crystal elastomer", "piezoelectric ceramic",
        "shape-memory alloy", "ferrofluid", "superconducting YBCO tape", "halide perovskite film",
        "carbon nanotube forest", "stimuli-responsive hydrogel", "bacterial cellulose membrane", "metallic glass",
        "silica aerogel foam", "photonic crystal", "topological insulator", "ionic liquid",
        "magnetostrictive alloy", "synthetic opal", "MXene film", "self-healing polymer",
        "quantum dot array", "bismuth telluride thermoelectric", "molten salt", "electret polymer",
    ],
    "organism": [
        "swordfish (Xiphias gladius) blood proteins", "tardigrade damage-suppressor protein", "electric eel electrocytes",
        "mantis shrimp dactyl club", "spider silk", "diatom silica shell", "magnetotactic bacteria",
        "deep-sea tube worm hemoglobin", "Antarctic icefish antifreeze proteins", "gecko foot setae",
        "lotus leaf surface", "firefly luciferase", "Namib desert beetle shell", "bombardier beetle reaction chamber",
        "archaeal extremophile enzymes", "octopus chromatophores", "tree xylem sap transport", "slime mold network",
        "mussel adhesive proteins", "bat echolocation organ", "kelp holdfast", "cyanobacteria carboxysome",
        "hummingbird feather structure", "pitcher plant surface",
    ],
    "phenomenon": [
        "quantum tunnelling", "Casimir effect", "Bose-Einstein condensation", "Marangoni convection",
        "triboelectric charging", "Seebeck effect", "sonoluminescence", "Leidenfrost effect",
        "superfluid helium flow", "Hall effect", "Faraday rotation", "acoustic cavitation", "Raman scattering",
        "electrowetting", "spin-orbit torque", "Brownian ratchet", "nuclear magnetic resonance",
        "evanescent wave coupling", "Peltier cooling", "Bernoulli effect", "photoelectric effect",
        "phase separation", "shock wave focusing", "parametric resonance",
    ],
    "condition": [
        "ultra-high vacuum", "10 GPa static pressure", "cryogenic temperature near 4 K", "strong 10 T magnetic field",
        "microgravity", "rapid thermal cycling", "ultrasonic standing wave", "high-voltage pulsed discharge",
        "ionizing radiation field", "supercritical CO2", "low-pressure plasma", "rotating frame at high angular velocity",
        "femtosecond laser pulses", "vacuum ultraviolet illumination", "strong electric field gradient",
        "extreme shear flow", "deep-sea hydrostatic pressure", "low ambient pressure at high altitude",
        "electrochemical potential sweep", "microwave resonant cavity",
    ],
    "principle": [
        "resonance", "self-assembly", "topological protection", "feedback control loop", "symmetry breaking",
        "percolation threshold", "entropy-driven ordering", "impedance matching", "phase locking",
        "stochastic resonance", "gradient-driven transport", "autocatalysis", "error-correcting redundancy",
        "hierarchical structuring", "adiabatic invariants", "energy-ledger bookkeeping", "evolutionary optimization",
        "metamaterial effective medium", "coherent superposition", "dissipative structures",
    ],
}


def concept_category(concept: str) -> Optional[str]:
    for category, items in CONCEPT_BANK.items():
        if concept in items:
            return category
    return None


def sample_concepts(rng: random.Random, n: int = 3, goal_text: str = "") -> List[str]:
    """
    Picks `n` concepts from DIFFERENT categories (so they are as unrelated as possible),
    skipping any concept whose words already appear in the goal.
    """
    goal_words = set(re.findall(r"[a-z]{4,}", goal_text.lower()))
    categories = list(CONCEPT_BANK)
    rng.shuffle(categories)
    picked: List[str] = []
    for category in categories[:max(1, min(n, len(categories)))]:
        options = [c for c in CONCEPT_BANK[category]
                   if not (set(re.findall(r"[a-z]{4,}", c.lower())) & goal_words)]
        if options:
            picked.append(rng.choice(options))
    return picked
