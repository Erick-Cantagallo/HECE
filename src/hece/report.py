# HECE/src/hece/report.py
import os
from datetime import datetime, timezone
from typing import List
from hece.core.models.base import GoalAnalysis, KnowledgeContext, ConstraintContext, Hypothesis, ScientificReport

class ReportGenerator:
    """
    Compiles all pipeline contexts into a final ScientificReport 
    and exports it to a readable format (Markdown).
    """
    def generate_report(self, analysis: GoalAnalysis, knowledge: KnowledgeContext, constraints: ConstraintContext, hypotheses: List[Hypothesis]) -> ScientificReport:
        # Calculate a mock global confidence based on active/speculative hypotheses
        active_hyps = [h for h in hypotheses if h.status in ["active", "speculative"]]
        global_conf = sum(h.confidence for h in active_hyps) / len(active_hyps) if active_hyps else 0.1
        
        return ScientificReport(
            goal=analysis.goal,
            constraints=analysis.extracted_constraints,
            hypotheses=hypotheses,
            summary=f"Investigation into {analysis.goal.domain or 'general'} domain yielded {len(hypotheses)} structured hypotheses.",
            conclusion="Pipeline execution completed successfully. Hypothesis ready for human or AI review.",
            confidence_global=round(global_conf, 2)
        )

    def export_to_markdown(self, report: ScientificReport, output_dir: str = "reports") -> str:
        """Exports the Pydantic report object to a physical Markdown file."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(output_dir, f"HECE_Report_{timestamp}.md")
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write("# HECE Scientific Report\n\n")
            f.write(f"**Goal ID:** `{report.goal.id}`\n")
            f.write(f"**Domain:** `{report.goal.domain.upper() if report.goal.domain else 'GENERAL'}`\n")
            f.write(f"**Objective:** {report.goal.description}\n\n")
            
            f.write("## Executive Summary\n")
            f.write(f"{report.summary}\n\n")
            
            f.write("## Generated Hypotheses\n")
            for h in report.hypotheses:
                f.write(f"### [{h.status.upper()}] Hypothesis (ID: {h.id[:8]})\n")
                f.write(f"- **Description:** {h.description}\n")
                # Using :.0f to eliminate floating point artifacts
                f.write(f"- **Feasibility Score:** {h.feasibility_score * 100:.0f}%\n")
                f.write(f"- **Confidence Level:** {h.confidence * 100:.0f}%\n\n")
                
            f.write("## Conclusion\n")
            f.write(f"{report.conclusion}\n")
            
        return filename