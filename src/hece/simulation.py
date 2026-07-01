# HECE/src/hece/simulation.py
from typing import List
from hece.core.models.base import Hypothesis, ConstraintContext

class SimulationEngine:
    """
    Evaluates hypotheses using a strict, deterministic mathematical model.
    It does NOT rely on AI for the final score, but computes penalties 
    based on the length of flaw arrays extracted during synthesis.
    """
    
    def evaluate(self, hypotheses: List[Hypothesis], boundaries: ConstraintContext) -> List[Hypothesis]:
        for hyp in hypotheses:
            base_score = 1.0 # Starts at 100% viability
            
            # 1. Fatal Physics/Constraint Violations (-40% each)
            if hyp.violated_hard_constraints:
                base_score -= 0.40 * len(hyp.violated_hard_constraints)
                
            # 2. Logical Flaws identified by the Critic (-15% each)
            if hyp.logical_flaws:
                base_score -= 0.15 * len(hyp.logical_flaws)
                
            # 3. Speculative Assumptions (-5% each)
            if hyp.assumptions:
                base_score -= 0.05 * len(hyp.assumptions)
                
            # Mathematical clamping to keep it strictly between 0.0 and 1.0
            # FIX: Added round(..., 2) to eliminate floating point precision anomalies
            hyp.feasibility_score = round(max(0.0, min(1.0, base_score)), 2)
            
            # Status Deterministic Assignment
            if hyp.feasibility_score >= 0.70:
                hyp.status = "active"
            elif hyp.feasibility_score >= 0.40:
                hyp.status = "speculative"
            else:
                hyp.status = "rejected"
                
        return hypotheses