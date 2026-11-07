# HECE/src/hece/pipeline.py
"""One entry point for inventor mode, shared by the Streamlit app, the CLI and the tests."""
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, List, Optional

from hece.conclusion import build_discovery_conclusion
from hece.constraints import ConstraintEngine
from hece.core.models.base import ConstraintContext, GoalAnalysis, KnowledgeContext
from hece.explorer import DiscoveryConfig, DiscoveryEngine, DiscoveryResult
from hece.interpreter import GoalInterpreter
from hece.knowledge import KnowledgeEngine
from hece.paper import PaperGenerator


@dataclass
class DiscoveryRun:
    analysis: GoalAnalysis
    context: KnowledgeContext
    boundaries: ConstraintContext
    result: DiscoveryResult
    conclusion: str
    json_path: str
    pdf_path: Optional[str] = None


def offline_context(analysis: GoalAnalysis) -> KnowledgeContext:
    """Context without any literature search: the ideas come only from the model's own knowledge."""
    axioms = KnowledgeEngine.DOMAIN_AXIOMS
    domain = analysis.goal.domain or "general"
    laws = axioms.get(domain) or (axioms["physics"] + axioms["engineering"])
    return KnowledgeContext(
        goal_id=analysis.goal.id, domain_laws=list(laws),
        known_facts=["Literature retrieval is disabled: ideas come from the model's own knowledge and are "
                     "NOT grounded in retrieved sources."])


def run_discovery(project_name: str, goal: str, config: Optional[DiscoveryConfig] = None, use_rag: bool = True,
                  on_event: Optional[Callable[[str], None]] = print, should_stop: Optional[Callable[[], bool]] = None,
                  make_pdf: bool = True, runs_dir: str = "runs",
                  requirements: Optional[List[str]] = None) -> DiscoveryRun:
    emit = on_event or (lambda m: None)
    config = config or DiscoveryConfig()

    emit("Interpreting the goal...")
    analysis = GoalInterpreter().analyze(goal)

    if use_rag:
        emit("Retrieving literature (optional context)...")
        context = KnowledgeEngine().retrieve_context(analysis)
    else:
        context = offline_context(analysis)

    emit("Establishing the laws that must hold...")
    boundaries = ConstraintEngine().process_constraints(analysis, context)

    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", project_name).strip("_") or "run"
    json_path = os.path.join(runs_dir, f"HECE_{slug}_{stamp}.json")

    emit(f"Exploring (up to {config.max_iterations} attempts, target {config.target_count} candidate(s))...")
    engine = DiscoveryEngine(config=config, on_event=emit, should_stop=should_stop)
    result = engine.run(analysis, context, boundaries, save_path=json_path, requirements=requirements)

    conclusion = build_discovery_conclusion(result)
    pdf_path = None
    if make_pdf:
        emit("Publishing the report (PDF)...")
        shown = result.accepted or result.near_misses(3)
        pdf_path = PaperGenerator.generate_pdf(project_name, analysis, context, boundaries, shown, conclusion,
                                               exploration_log=result.exploration_log(),
                                               requirements=result.requirements,
                                               requirements_source=result.requirements_source)
    return DiscoveryRun(analysis, context, boundaries, result, conclusion, json_path, pdf_path)
