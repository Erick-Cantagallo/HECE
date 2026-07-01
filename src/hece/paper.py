# HECE/src/hece/paper.py
import os
from datetime import datetime
from fpdf import FPDF
from hece.core.models.base import GoalAnalysis, KnowledgeContext, ConstraintContext, Hypothesis
from typing import List

def _sanitize_text(text: str) -> str:
    """
    Strips highly problematic unicode but retains basic math symbols.
    Uses latin-1 to safely render standard text and basic equations in FPDF.
    """
    if not text:
        return ""
    # Use latin-1 to allow basic symbols (+, -, =, etc) instead of pure ascii
    safe = text.encode('latin-1', 'replace').decode('latin-1')
    safe = safe.replace('\t', '    ')
    # Force FPDF to not panic on weird hidden characters
    safe = safe.replace('?', '?') 
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
        The ultimate safe print. Hardcodes width to ignore broken margin states,
        and forces cursor back to safety before drawing.
        """
        self.set_x(10) # Slam cursor to the left margin
        safe_text = _sanitize_text(text)
        
        try:
            # A4 is 210mm wide. 210 - 20mm (10mm each side) = 190mm hardcoded width
            # This completely ignores fpdf2's internal 'remaining space' bugs
            effective_width = self.w - 20 
            self.multi_cell(effective_width, 6, safe_text)
        except Exception:
            # If the universe collapses, write a raw string
            self.set_x(10)
            self.write(6, "[PDF ENGINE ERROR: Omitted unrenderable text block]\n")

class PaperGenerator:
    @staticmethod
    def generate_pdf(analysis: GoalAnalysis, context: KnowledgeContext, boundaries: ConstraintContext, hypotheses: List[Hypothesis]) -> str:
        pdf = ScientificPaper()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # 1. Title
        pdf.set_font("helvetica", "B", 18)
        pdf._indestructible_print(f"Research Investigation:\n{analysis.goal.description}")
        
        # 2. Abstract (RAG Context)
        pdf.chapter_title("1. Abstract & Real-World Literature")
        pdf.set_font("helvetica", "", 11)
        abstract_text = "This paper investigates the given goal by consulting current scientific literature.\n\n"
        abstract_text += "\n".join(context.known_facts)
        pdf._indestructible_print(abstract_text)

        # 3. Methodology (Constraints)
        pdf.chapter_title("2. Methodology & Constraints")
        pdf.set_font("helvetica", "", 11)
        meth_text = "The generation of hypotheses was constrained by the following absolute laws:\n"
        for hc in boundaries.hard_constraints:
            meth_text += f"- {hc}\n"
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

        # 5. Conclusion
        pdf.chapter_title("4. Conclusion")
        pdf.set_font("helvetica", "", 11)
        active = sum(1 for h in hypotheses if h.status == 'active')
        conclusion_text = f"The HECE pipeline evaluated {len(hypotheses)} hypotheses. {active} hypotheses passed the strict deterministic evaluation and are recommended for further human peer review."
        pdf._indestructible_print(conclusion_text)

        # Save PDF
        os.makedirs("reports", exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"reports/HECE_Paper_{timestamp}.pdf"
        pdf.output(filename)
        return filename