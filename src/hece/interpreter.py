# HECE/src/hece/interpreter.py
import re
import uuid
from typing import List
from hece.core.models.base import Goal, Constraint, GoalAnalysis

class GoalInterpreter:
    """
    Deterministic engine to decompose and analyze a user goal.
    Filters scientific 'fluff' to prevent RAG Poisoning and safely detects domains.
    """
    
    DOMAIN_KNOWLEDGE = {
        "physics": ["gravity", "quantum", "relativity", "energy", "mass", "force", "velocity", "time", "thermodynamics", "optics"],
        "biology": ["cell", "dna", "evolution", "organism", "genetics", "virus", "life", "protein"],
        "chemistry": ["molecule", "reaction", "atom", "element", "catalyst", "acid", "graphene", "oxide", "polymer", "membrane", "desalination"],
        "computer_science": ["algorithm", "data", "computation", "artificial intelligence", "software", "code", "neural"],
        "engineering": ["efficiency", "machine", "engine", "structure", "material", "nanotechnology"]
    }

    STOPWORDS = {
        "the", "a", "an", "is", "are", "how", "what", "why", "to", "do", "does", "can", "in", "on", "of", "for", "with", "without",
        "and", "or", "by", "from", "using", "method", "novel", "new", "approach", "study", "research", "system", "high-efficiency",
        "high", "efficiency", "about", "this", "build", "create", "design", "investigate", "make", "development", "via",
        "want", "wants", "need", "like", "would", "could", "should", "get", "use", "please", "way", "able", "something", "some",
        "reduce", "reduction", "improve", "increase", "decrease", "enhance", "optimize", "minimize", "maximize", "achieve",
        "develop", "find", "solve", "understand", "explain", "better", "more", "less", "lower", "higher", "consumption"
    }

    def extract_keywords(self, text: str) -> List[str]:
        """Filters fluff words and puts known scientific terms first (the search uses the first 3)."""
        tokens = re.findall(r"[a-z][a-z\-]+", text.lower())
        kept = list(dict.fromkeys(t for t in tokens if t not in self.STOPWORDS and len(t) > 2))
        vocab = {t for terms in self.DOMAIN_KNOWLEDGE.values() for t in terms}
        return sorted(kept, key=lambda t: t not in vocab)

    def detect_primary_domain(self, keywords: List[str]) -> str:
        """
        Safely scores and detects the scientific domain using explicit primitives.
        Bypasses the max() built-in to guarantee execution in all Python environments.
        """
        if not hasattr(self, 'DOMAIN_KNOWLEDGE') or not self.DOMAIN_KNOWLEDGE:
            return "general"
            
        domain_scores = {domain: 0 for domain in self.DOMAIN_KNOWLEDGE.keys()}
        
        # 1. Calculate scores based on keyword matches
        for keyword in keywords:
            for domain, terms in self.DOMAIN_KNOWLEDGE.items():
                if keyword in terms:
                    domain_scores[domain] += 1
                    
        # 2. Explicit primitive loop (replaces max() and all() functions)
        best_domain = "general"
        highest_score = 0
        
        for domain, score in domain_scores.items():
            if score > highest_score:
                highest_score = score
                best_domain = domain
                
        # If no keywords matched, highest_score remains 0, and it naturally returns "general"
        return best_domain

    def estimate_complexity(self, keywords: List[str]) -> int:
        base_complexity = 5
        base_complexity += min(len(keywords), 4) 
        return min(base_complexity, 10)

    def identify_constraints(self, text: str) -> List[Constraint]:
        constraints = []
        text_lower = text.lower()
        
        if "without" in text_lower:
            constraints.append(Constraint(
                id=str(uuid.uuid4()),
                description="Exclusion condition detected (e.g., 'without')",
                type="methodological",
                strictness=8
            ))
        if "only" in text_lower or "limited to" in text_lower:
            constraints.append(Constraint(
                id=str(uuid.uuid4()),
                description="Limitation condition detected",
                type="methodological",
                strictness=9
            ))
            
        return constraints

    def analyze(self, user_goal: str) -> GoalAnalysis:
        keywords = self.extract_keywords(user_goal)
        domain = self.detect_primary_domain(keywords)
        complexity = self.estimate_complexity(keywords)
        constraints = self.identify_constraints(user_goal)

        goal = Goal(
            id=str(uuid.uuid4()),
            description=user_goal,
            domain=domain,
            complexity_level=complexity
        )

        return GoalAnalysis(
            goal=goal,
            keywords=keywords,
            extracted_constraints=constraints
        )