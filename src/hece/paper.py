# HECE/src/hece/paper.py
import os
import re
from datetime import datetime
from fpdf import FPDF
from hece.core.models.base import GoalAnalysis, KnowledgeContext, ConstraintContext, Hypothesis
from typing import List, Optional

_GREEK = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "ζ": "zeta", "η": "eta", "θ": "theta",
          "κ": "kappa", "λ": "lambda", "μ": "\u00b5", "ν": "nu", "ξ": "xi", "π": "pi", "ρ": "rho", "σ": "sigma", "τ": "tau",
          "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega", "Γ": "Gamma", "Δ": "Delta", "Θ": "Theta", "Λ": "Lambda",
          "Π": "Pi", "Σ": "Sigma", "Φ": "Phi", "Ψ": "Psi", "Ω": "Omega", "ℏ": "hbar", "≈": "~", "≤": "<=", "≥": ">=",
          "→": "->", "−": "-", "–": "-", "—": "-", "’": "'", "‘": "'", "“": "'", "”": "'"}
_TRANSLIT = {ord(k): v for k, v in _GREEK.items()}
_SUP_RUN = re.compile(r"[\u2070\u00b9\u00b2\u00b3\u2074-\u2079\u207a\u207b]+")
_SUP_MAP = str.maketrans("\u2070\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u207a\u207b", "012345678 9+-".replace(" ", "")[:12])


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
    
    safe = _SUP_RUN.sub(lambda m: "^" + m.group(0).translate(_SUP_MAP), safe)  # m\u00b2 s\u207b\u00b2 -> m^2 s^-2
    safe = safe.translate(_TRANSLIT)  # keep Greek letters/symbols readable instead of '?'
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
    def generate_pdf(project_name: str, analysis: GoalAnalysis, context: KnowledgeContext, boundaries: ConstraintContext, hypotheses: List[Hypothesis], deep_conclusion: str,
                     exploration_log: Optional[List[dict]] = None,
                     requirements: Optional[List[str]] = None, requirements_source: str = "model") -> str:
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
        meth_text += "The AI proposes an initial viability estimate; the Python Simulation Engine then applies these rules in order:\n"
        meth_text += "  1. Substance Lock: a description under 50 words scores 0%.\n"
        meth_text += "  2. Any VERIFIED violation of a hard constraint (law and quote checked by Python) scores 0%.\n"
        meth_text += "  3. Otherwise: AI estimate, minus 15% per logical flaw, 15% per red flag (known pseudo-scientific patterns), 5% per unproven assumption and 10% per unverified accusation.\n"
        meth_text += "  4. A hypothesis is accepted only with a final score of at least 65%.\n"
        meth_text += "  5. Acceptance means automated screening only; accepted hypotheses still require expert review."
        if exploration_log:
            meth_text += "\n\nC. INVENTOR MODE (speculative exploration):\n"
            meth_text += "  - The engine explores many mechanism families; every attempt is logged in section 5.\n"
            meth_text += "  - Each hypothesis must state a numeric, falsifiable PREDICTION and a REFUTATION condition (Falsifiability Lock: otherwise 0%).\n"
            meth_text += "  - New physical quantities or laws may be postulated, but each must declare SI dimensions, a coupling, and the condition under which it reduces to known physics. Each postulate costs 10%.\n"
            meth_text += "  - The listed physical laws remain hard constraints: postulates extend them, they never override them.\n"
            meth_text += "  - Ideas come from the model's own knowledge unless literature is listed in section 1. They are speculative candidates for experiments, not established science."
        pdf._indestructible_print(meth_text)

        # 4. Proposed Hypotheses
        pdf.chapter_title("3. Proposed Hypotheses")
        for i, hyp in enumerate(hypotheses, 1):
            pdf.set_font("helvetica", "B", 12)
            pdf.set_x(10)
            pdf.cell(0, 8, f"Hypothesis {i} [{hyp.status.upper()}] - Viability: {hyp.feasibility_score * 100:.0f}%", new_x="LMARGIN", new_y="NEXT")
            
            pdf.set_font("helvetica", "", 11)
            pdf._indestructible_print(hyp.description)

            if hyp.strategy:
                pdf.set_font("helvetica", "I", 9)
                pdf._indestructible_print(
                    f"Strategy: {hyp.strategy} | family: {hyp.family}"
                    + (f" | seeds: {' + '.join(hyp.concepts)}" if hyp.concepts else ""))
                if hyp.target:
                    pdf._indestructible_print(f"Target requirement: {hyp.target}")

            est = f"{hyp.ai_estimate * 100:.0f}%" if hyp.ai_estimate is not None else "n/a"
            pdf.set_font("helvetica", "I", 9)
            pdf._indestructible_print(
                f"Audit: AI estimate {est} | logical flaws: {len(hyp.logical_flaws)} | "
                f"assumptions: {len(hyp.assumptions)} | unverified accusations: {len(hyp.unverified_violations)} | "
                f"human review: {'yes' if hyp.needs_human_review else 'no'}")
            for label, items in (("Logical flaws", hyp.logical_flaws), ("Assumptions", hyp.assumptions),
                                 ("Numeric inconsistencies (verified by Python)", hyp.numeric_flags),
                                 ("Red flags (deterministic screen)", hyp.red_flags),
                                 ("Speculative notes", hyp.speculative_notes),
                                 ("Unverified accusations (not applied)", hyp.unverified_violations)):
                if items:
                    pdf._indestructible_print(f"{label}: " + "; ".join(str(i) for i in items))
            if hyp.confirmation_scores:
                pdf._indestructible_print("Independent confirmation rounds: " + ", ".join(f"{x * 100:.0f}%" for x in hyp.confirmation_scores))
            if hyp.status == "active":
                pdf._indestructible_print("Passed automated screening only. Not validated by experiment; expert review required.")
            for ev in hyp.violation_evidence:
                pdf._indestructible_print(f"Proof of violation: {ev}")
            pdf.set_font("helvetica", "", 11)
            
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

        if exploration_log:
            pdf.chapter_title("5. Exploration Map")
            pdf.set_font("helvetica", "", 10)
            if requirements:
                pdf._indestructible_print(("Requirements supplied by the user:\n" if requirements_source == "user" else "Requirements derived from the goal (model-derived, not verified):\n")
                                          + "\n".join(f"  R{k}: {text}" for k, text in enumerate(requirements, 1)) + "\n")
            for row in exploration_log:
                seeds = f" | seeds: {' + '.join(row['concepts'])}" if row.get("concepts") else ""
                parent = f" | improves #{row['parent']}" if row.get("parent") else ""
                score = f"{row['score'] * 100:.0f}%" if row.get("score") is not None else "n/a"
                tag = f" [R{row['target']}]" if row.get("target") else ""
                line = f"#{row['n']} {str(row['strategy']).upper()}{tag}{parent}{seeds} | {row.get('family') or '(no valid candidate)'} | {row['outcome']} {score}"
                if row.get("reason") and row["outcome"] != "accepted":
                    line += f"\n    barrier: {row['reason'][:300]}"
                pdf._indestructible_print(line)

        # Save PDF with Custom Name
        os.makedirs("reports", exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        safe_filename = project_name.replace(' ', '_').replace('/', '_')
        filename = f"reports/HECE_{safe_filename}_{timestamp}.pdf"
        pdf.output(filename)
        return filename