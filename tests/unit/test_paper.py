# HECE/tests/unit/test_paper.py
import pytest
from unittest.mock import patch
from hece.paper import PaperGenerator, _sanitize_text
from hece.core.models.base import GoalAnalysis, KnowledgeContext, ConstraintContext, Hypothesis, Goal

def test_sanitize_text():
    """Ensures that tabs are replaced and text survives encoding boundaries."""
    dirty_text = "This is a test \t with a tab and some weird chars."
    clean_text = _sanitize_text(dirty_text)
    
    assert "\t" not in clean_text
    assert "    " in clean_text
    assert len(clean_text) > 0

@patch('hece.paper.FPDF.output')
def test_generate_pdf(mock_output):
    """
    Ensures the PDF compiles correctly and tries to save, 
    but we mock the output to prevent writing physical files during tests.
    """
    goal = Goal(id="pdf-test", description="Test PDF Generation")
    analysis = GoalAnalysis(goal=goal)
    context = KnowledgeContext(goal_id="pdf-test", known_facts=["Mocked Fact 1"])
    boundaries = ConstraintContext(goal_id="pdf-test", hard_constraints=["Mocked Law 1"])
    
    hypothesis = Hypothesis(
        id="hyp-1",
        goal_id="pdf-test",
        description="A test hypothesis with a math formula $E = mc^2$.",
        feasibility_score=0.9
    )
    
    # Execute
    filename = PaperGenerator.generate_pdf(analysis, context, boundaries, [hypothesis])
    
    # Assertions
    assert filename.startswith("reports/HECE_Paper_")
    assert filename.endswith(".pdf")
    # Verifies if the system actually commanded the PDF to be saved
    mock_output.assert_called_once()