# HECE/src/hece/simulation.py
from typing import List
from hece.core.models.base import Hypothesis, ConstraintContext

class SimulationEngine:
    """
    Evaluates hypotheses against scientific constraints and evidence.
    Adjusts feasibility scores and confidence levels deterministically.
    """
    
    def evaluate(self, hypotheses: List[Hypothesis], constraints: ConstraintContext) -> List[Hypothesis]:
        """
        Runs a heuristic evaluation (mock simulation) over the hypotheses.
        """
        evaluated_hypotheses = []
        
        for hyp in hypotheses:
            score_modifier = 0.0
            
            # 1. Reward strong supporting evidence
            if hyp.supporting_evidence:
                score_modifier += 0.15 * len(hyp.supporting_evidence)
                
            # 2. Penalize lack of strict required conditions
            if not hyp.required_conditions:
                score_modifier -= 0.2
                
            # 3. Penalize conflicting evidence
            if hyp.conflicting_evidence:
                score_modifier -= 0.3 * len(hyp.conflicting_evidence)
                
            # Recalculate feasibility (capped between 0.0 and 1.0)
            new_feasibility = min(max(hyp.feasibility_score + score_modifier, 0.0), 1.0)
            hyp.feasibility_score = round(new_feasibility, 2)
            
            # Update status based on strict thresholds
            if hyp.feasibility_score >= 0.6:
                hyp.status = "active"
            elif hyp.feasibility_score < 0.3:
                hyp.status = "rejected"
            else:
                hyp.status = "speculative"
                
            evaluated_hypotheses.append(hyp)
            
        return evaluated_hypotheses