# HECE/src/hece/knowledge.py
from typing import List, Dict
from hece.core.models.base import GoalAnalysis, KnowledgeContext
from hece.tools import ScientificToolbox

class KnowledgeEngine:
    """
    Retrieves foundational laws and performs RAG (Retrieval-Augmented Generation) 
    to inject real-world scientific literature into the context.
    """
    # ... (Axiomas existentes mantidos)
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
        ]
    }

    def retrieve_context(self, analysis: GoalAnalysis) -> KnowledgeContext:
        """
        Processes the GoalAnalysis to inject domain-specific laws and real-world data.
        """
        domain = analysis.goal.domain or "general"
        
        # 1. Inject Domain Laws
        laws = self.DOMAIN_AXIOMS.get(domain, ["General Scientific Method rules apply"])
        
        # 2. RAG: Fetch real literature based on keywords
        print("    -> [RAG] Searching ArXiv database for real-world context...")
        search_query = " ".join(analysis.keywords[:3]) # Use top 3 keywords
        external_facts = ScientificToolbox.search_arxiv(search_query)
        
        facts = [
            f"Established literature and basic frameworks exist for {domain}.",
            external_facts # Injetando os artigos científicos reais
        ]
        
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