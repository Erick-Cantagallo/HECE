# HECE/tests/unit/test_interpreter.py
import pytest
from hece.interpreter import GoalInterpreter
from hece.core.models.base import GoalAnalysis

@pytest.fixture
def interpreter():
    return GoalInterpreter()

def test_extract_keywords(interpreter):
    text = "How does quantum gravity work without string theory?"
    keywords = interpreter.extract_keywords(text)
    # Verifica se as stopwords foram removidas e as palavras reais mantidas
    assert "quantum" in keywords
    assert "gravity" in keywords
    assert "how" not in keywords

def test_detect_primary_domain_physics(interpreter):
    keywords = ["quantum", "gravity", "mass"]
    domain = interpreter.detect_primary_domain(keywords)
    assert domain == "physics"

def test_detect_primary_domain_biology(interpreter):
    keywords = ["cell", "dna", "evolution"]
    domain = interpreter.detect_primary_domain(keywords)
    assert domain == "biology"

def test_identify_constraints_without(interpreter):
    text = "simulate gravity without strings"
    constraints = interpreter.identify_constraints(text)
    assert len(constraints) > 0
    assert constraints[0].type == "methodological"
    assert "without" in constraints[0].description.lower()

def test_full_analyze_pipeline(interpreter):
    goal_text = "How to cure a virus only using biology?"
    analysis = interpreter.analyze(goal_text)
    
    assert isinstance(analysis, GoalAnalysis)
    assert analysis.goal.domain == "biology"
    assert analysis.goal.complexity_level >= 3
    assert len(analysis.extracted_constraints) == 1
    assert "limitation" in analysis.extracted_constraints[0].description.lower()