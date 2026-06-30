# HECE/src/hece/constraints.py
from hece.core.models.base import GoalAnalysis, KnowledgeContext, ConstraintContext

class ConstraintEngine:
    """
    Fuses user constraints and scientific knowledge into strict boundaries.
    These boundaries will act as the 'guardrails' for the AI in Sprint 4.
    """

    def process_constraints(self, analysis: GoalAnalysis, knowledge: KnowledgeContext) -> ConstraintContext:
        """
        Evaluates and categorizes all inputs into Hard and Soft rules.
        """
        hard_constraints = []
        soft_constraints = []
        evaluation_criteria = []

        # 1. Scientific Laws are ALWAYS Hard Constraints
        for law in knowledge.domain_laws:
            hard_constraints.append(f"MUST NOT VIOLATE: {law}")

        # 2. Process User/Extracted Constraints based on strictness
        for constraint in analysis.extracted_constraints:
            if constraint.strictness >= 8:
                hard_constraints.append(f"USER REQUIREMENT (STRICT): {constraint.description}")
            else:
                soft_constraints.append(f"USER PREFERENCE: {constraint.description}")

        # 3. Transform Scientific Limitations into Evaluation Criteria
        for limitation in knowledge.current_limitations:
            evaluation_criteria.append(f"Hypothesis must address this limitation: {limitation}")

        # 4. Inject Baseline Scientific Criteria
        evaluation_criteria.append("Must be logically consistent and mathematically sound.")
        evaluation_criteria.append(f"Must actively solve or explore: '{analysis.goal.description}'")

        return ConstraintContext(
            goal_id=analysis.goal.id,
            hard_constraints=hard_constraints,
            soft_constraints=soft_constraints,
            evaluation_criteria=evaluation_criteria
        )