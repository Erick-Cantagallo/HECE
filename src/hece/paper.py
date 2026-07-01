# HECE/src/hece/paper.py
import os
from datetime import datetime
from fpdf import FPDF
from hece.core.models.base import GoalAnalysis, KnowledgeContext, ConstraintContext, Hypothesis
from typing import List

def _sanitize_text(text: str) -> str:
    """
    Strips problematic characters entirely.
    Removes rogue markdown (like **) and standardizes quotes.
    Translates LaTeX remnants to readable plain text if the LLM rebels.
    """
    if not text:
        return ""
    
    # Remove markdown bolding and replace double quotes with single to avoid hanging quotes
    safe = text.replace('**', '')
    safe = safe.replace('"', "'")
    
    # Aggressive LaTeX and Math symbol cleaner for FPDF compatibility
    safe = safe.replace('$', '')
    safe = safe.replace('\\frac', ' / ')
    safe = safe.replace('\\partial', 'd')
    safe = safe.replace('\\', '') # Catch-all for remaining backslashes
    
    safe = safe.encode('latin-1', 'replace').decode('latin-1')
    safe = safe.replace('\t', '    ')
    return safe

class ScientificPaper(FPDF):
    def header(self):
        self.set_font("helvetica", "B", 12)
        self.set_x(10)
        self.cell(0, 10, "HECE - Autonomous Scientific Investigation", border=False, new_x="LMARGIN", new_y="NEXT", align="C")
        self.line(10, 20, 200, 20)
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("helvetica", "I", 8)
        self.set_x(10)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    def chapter_title(self, title):
        self.ln(5)
        self.set_font("helvetica", "B", 14)
        self.set_x(10)
        self.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align="L")
        self.ln(2)

    def _indestructible_print(self, text: str):
        """
        Hardcodes width to ignore broken margin states,
        and forces cursor back to safety before drawing.
        """
        self.set_x(10)
        safe_text = _sanitize_text(text)
        
        try:
            effective_width = self.w - 20 
            self.multi_cell(effective_width, 6, safe_text)
        except Exception:
            self.set_x(10)
            self.write(6, "[PDF ENGINE ERROR: Omitted unrenderable text block]\n")

class PaperGenerator:
    @staticmethod
    def generate_pdf(project_name: str, analysis: GoalAnalysis, context: KnowledgeContext, boundaries: ConstraintContext, hypotheses: List[Hypothesis], deep_conclusion: str) -> str:
        pdf = ScientificPaper()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # 1. Title
        pdf.set_font("helvetica", "B", 18)
        pdf._indestructible_print(f"Project: {project_name.upper()}\nInvestigation: {analysis.goal.description}")
        
        # 2. Abstract (RAG Context)
        pdf.chapter_title("1. Abstract & Real-World Literature")
        pdf.set_font("helvetica", "", 11)
        abstract_text = "This paper investigates the given goal by consulting current scientific literature.\n\n"
        abstract_text += "\n".join(context.known_facts)
        pdf._indestructible_print(abstract_text)

        # 3. Methodology & Metrics (NEW SECTION)
        pdf.chapter_title("2. Methodology & Viability Metrics")
        pdf.set_font("helvetica", "", 11)
        meth_text = "A. SCIENTIFIC BOUNDARIES (HARD CONSTRAINTS):\n"
        for hc in boundaries.hard_constraints:
            meth_text += f"- {hc}\n"
            
        meth_text += "\nB. VIABILITY SCORE CALCULATION:\n"
        meth_text += "The Feasibility Score is calculated deterministically by the Python Simulation Engine, NOT by the AI. "
        meth_text += "The base score starts at 100%. Mathematical penalties are applied based on flaws identified during the investigation:\n"
        meth_text += "  [-] 40% penalty per Violated Hard Constraint (Physics/Thermodynamics laws broken).\n"
        meth_text += "  [-] 15% penalty per Logical Flaw identified by the AI Critic.\n"
        meth_text += "  [-] 5% penalty per Unproven Assumption required.\n\n"
        meth_text += "Scores > 70% indicate high theoretical compatibility. Scores < 50% denote severe violations of known physics."
        pdf._indestructible_print(meth_text)

        # 4. Proposed Hypotheses
        pdf.chapter_title("3. Proposed Hypotheses")
        for i, hyp in enumerate(hypotheses, 1):
            pdf.set_font("helvetica", "B", 12)
            pdf.set_x(10)
            pdf.cell(0, 8, f"Hypothesis {i} [{hyp.status.upper()}] - Viability: {hyp.feasibility_score * 100:.0f}%", new_x="LMARGIN", new_y="NEXT")
            
            pdf.set_font("helvetica", "", 11)
            pdf._indestructible_print(hyp.description)
            
            if hyp.citations:
                pdf.set_font("helvetica", "I", 10)
                pdf.set_x(10)
                pdf.cell(0, 6, "Literature Citations:", new_x="LMARGIN", new_y="NEXT")
                for cit in hyp.citations:
                    pdf._indestructible_print(f"  [+] {cit}")
            pdf.ln(4)

        # 5. Deep Conclusion (Dynamic LLM Text)
        pdf.chapter_title("4. Conclusive Synthesis")
        pdf.set_font("helvetica", "", 11)
        active = sum(1 for h in hypotheses if h.status == 'active')
        pdf._indestructible_print(f"PIPELINE SUMMARY: Evaluated {len(hypotheses)} hypotheses. {active} hypotheses passed strict deterministic evaluation.\n")
        pdf._indestructible_print(f"DEEP ANALYSIS:\n{deep_conclusion}")

        # Save PDF with Custom Name
        os.makedirs("reports", exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_filename = project_name.replace(' ', '_').replace('/', '_')
        filename = f"reports/HECE_{safe_filename}_{timestamp}.pdf"
        pdf.output(filename)
        return filename