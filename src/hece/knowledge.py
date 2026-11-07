# HECE/src/hece/knowledge.py
from typing import List, Dict
from hece.core.models.base import GoalAnalysis, KnowledgeContext
from hece.tools import ScientificToolbox

class KnowledgeEngine:
    """
    Retrieves foundational laws and performs RAG (Retrieval-Augmented Generation) 
    to inject real-world scientific literature into the context.
    """
    
    # SPRINT FIX: Expanded Axioms to match the new Domain Knowledge from the Interpreter.
    DOMAIN_AXIOMS: Dict[str, List[str]] = {
        "physics": [
            "First Law of Thermodynamics (Energy cannot be created or destroyed)",
            "Second Law of Thermodynamics (Entropy increases)",
            "Speed of light in a vacuum is an absolute limit (c)"
        ],
        "biology": [
            "Cell theory (All living things are composed of cells)",
            "Evolution by natural selection",
            "Central dogma of molecular biology (DNA -> RNA -> Protein)"
        ],
        "chemistry": [
            "Conservation of mass in closed systems",
            "Thermodynamics of chemical equilibrium",
            "Pauli exclusion principle"
        ],
        "engineering": [
            "Conservation of mass and energy",
            "Material stress and strain limits",
            "Thermodynamic efficiency limits (Carnot limit)"
        ],
        "computer_science": [
            "Turing completeness limits (Halting problem)",
            "Information theory (Shannon entropy limits)"
        ]
    }

    def retrieve_context(self, analysis: GoalAnalysis) -> KnowledgeContext:
        """
        Processes the GoalAnalysis to inject domain-specific laws and real-world data.
        """
        domain = analysis.goal.domain or "general"
        
        # 1. Inject Domain Laws
        if domain in self.DOMAIN_AXIOMS:
            laws = self.DOMAIN_AXIOMS[domain]
        else:
            # Unknown domain: any physical device still obeys the universal physical limits.
            laws = ["General Scientific Method rules apply"] + self.DOMAIN_AXIOMS["physics"] + self.DOMAIN_AXIOMS["engineering"]
        
        # 2. RAG: fetch real literature; keep only papers that match the keywords
        print("    -> [RAG] Searching ArXiv database for real-world context...")
        search_keywords = analysis.keywords[:3]
        search_query = " ".join(search_keywords)
        print(f"    -> [RAG] Target Query: '{search_query}'")

        external_facts = ScientificToolbox.search_arxiv(search_query, keywords=search_keywords, use_cache=True) if search_keywords else ""

        if external_facts.strip():
            facts = [external_facts]
        elif ScientificToolbox.last_error:
            facts = [f"LITERATURE SEARCH FAILED for query '{search_query}' ({ScientificToolbox.last_error}). "
                     "Hypotheses are not grounded in retrieved sources."]
        else:
            facts = [f"NO RELEVANT LITERATURE WAS RETRIEVED for query '{search_query}'. "
                     "Hypotheses are not grounded in retrieved sources."]

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