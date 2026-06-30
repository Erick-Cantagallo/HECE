# HECE/src/hece/knowledge.py
from hece.core.models.base import GoalAnalysis, KnowledgeContext

class KnowledgeEngine:
    """
    Retrieves established scientific context for a given goal.
    In Sprint 2, this uses a deterministic knowledge base mapping.
    Later, this will connect to Vector Databases or external scientific APIs.
    """

    # Deterministic Knowledge Base (Axioms that cannot be violated)
    DOMAIN_AXIOMS = {
        "physics": [
            "First Law of Thermodynamics (Energy cannot be created or destroyed)",
            "Second Law of Thermodynamics (Entropy increases)",
            "Speed of light in a vacuum is an absolute limit (c)"
        ],
        "biology": [
            "Cell Theory (All living organisms are composed of cells)",
            "Central Dogma of Molecular Biology (DNA -> RNA -> Protein)",
            "Evolution by Natural Selection"
        ],
        "chemistry": [
            "Conservation of Mass",
            "Pauli Exclusion Principle"
        ],
        "computer_science": [
            "Halting Problem (Undecidability)",
            "Turing Completeness",
            "P vs NP unresolved boundary"
        ]
    }

    def retrieve_context(self, analysis: GoalAnalysis) -> KnowledgeContext:
        """
        Processes the GoalAnalysis to inject domain-specific laws, facts, and limitations.
        """
        # We ensure domain is always a string to satisfy strict type checking
        domain = analysis.goal.domain or "general"
        
        # 1. Inject Domain Laws
        laws = self.DOMAIN_AXIOMS.get(domain, ["General Scientific Method rules apply"])
        
        # 2. Inject Known Facts based on domain
        facts = [f"Established literature and basic frameworks exist for {domain}."]
        
        # 3. Inject Current Limitations heuristically
        limitations = []
        if analysis.goal.complexity_level >= 5:
            limitations.append("Problem exceeds standard theoretical frameworks.")
            
        if any(kw in ["quantum", "gravity"] for kw in analysis.keywords):
            limitations.append("Lack of a unified theory of quantum gravity.")

        return KnowledgeContext(
            goal_id=analysis.goal.id,
            domain_laws=laws,
            known_facts=facts,
            current_limitations=limitations
        )