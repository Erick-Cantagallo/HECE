# HECE/src/hece/interpreter.py
import uuid
from typing import List
from hece.core.models.base import Goal, Constraint, GoalAnalysis

class GoalInterpreter:
    """
    Deterministic engine to decompose and analyze a user goal.
    No LLM integration is used in this phase to ensure architectural validation.
    """
    
    # Deterministic domain mapping for Sprint 1
    DOMAIN_KNOWLEDGE = {
        "physics": ["gravity", "quantum", "relativity", "energy", "mass", "force", "velocity", "time"],
        "biology": ["cell", "dna", "evolution", "organism", "genetics", "virus", "life"],
        "chemistry": ["molecule", "reaction", "atom", "element", "catalyst", "acid"],
        "computer_science": ["algorithm", "data", "computation", "artificial intelligence", "software", "code"],
    }

    def extract_keywords(self, text: str) -> List[str]:
        # Remove punctuation and filter stopwords
        stopwords = {"the", "a", "an", "is", "are", "how", "what", "why", "to", "do", "does", "can", "in", "on", "of", "work", "for", "with", "without"}
        clean_text = text.lower().replace("?", "").replace(".", "").replace(",", "")
        words = clean_text.split()
        return [word for word in words if word not in stopwords and len(word) > 2]

    def detect_primary_domain(self, keywords: List[str]) -> str:
        domain_counts = {domain: 0 for domain in self.DOMAIN_KNOWLEDGE.keys()}
        for kw in keywords:
            for domain, terms in self.DOMAIN_KNOWLEDGE.items():
                if kw in terms:
                    domain_counts[domain] += 1
        
        # Select the domain with the highest keyword match
        max_domain = max(domain_counts, key=lambda k: domain_counts[k])
        return max_domain if domain_counts[max_domain] > 0 else "general"

    def estimate_complexity(self, keywords: List[str]) -> int:
        # Base complexity of 3, increases based on the number of scientific keywords
        score = 3 + (len(keywords) // 2)
        return min(score, 10) # Caps at 10 to respect the Goal model rule (le=10)

    def identify_constraints(self, text: str) -> List[Constraint]:
        constraints = []
        text_lower = text.lower()
        
        # Rule-based constraint extraction
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

        # Populate your existing Goal model
        goal = Goal(
            id=str(uuid.uuid4()),
            description=user_goal,
            domain=domain,
            complexity_level=complexity
        )

        # Return the final GoalAnalysis object
        return GoalAnalysis(
            goal=goal,
            keywords=keywords,
            extracted_constraints=constraints
        )