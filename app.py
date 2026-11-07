# HECE/app.py
import streamlit as st
import os

from hece.interpreter import GoalInterpreter
from hece.knowledge import KnowledgeEngine
from hece.constraints import ConstraintEngine
from hece.simulation import SimulationEngine
from hece.agents import AgentPool, InvestigationOrchestrator
from hece.paper import PaperGenerator
from hece.conclusion import build_conclusion
from hece.explorer import DiscoveryConfig
from hece.pipeline import run_discovery

# 1. Page Configuration (Must be the first Streamlit command)
st.set_page_config(page_title="HECE Laboratory", page_icon="🔬", layout="wide")

# 2. Header
st.title("🔬 HECE - Hypothesis & Creativity Engine")
st.markdown("### Autonomous Scientific Investigation Laboratory")
st.divider()

# 3. Sidebar (Controls)
with st.sidebar:
    st.header("⚙️ Project Parameters")
    mode = st.radio("Mode", ["🧪 Discovery (inventor)", "🔬 Classic investigation"], index=0,
                    help="Discovery explores many different mechanisms, remembers what failed and keeps trying new ones. "
                         "Classic generates a fixed number of hypotheses.")
    project_name = st.text_input("Project Name", value="Portal Gun Protocol")
    goal_description = st.text_area("Scientific Goal", value="I want to create a portal gun")

    st.markdown("---")
    st.markdown("**Compute Configuration**")
    if mode.startswith("🧪"):
        max_iterations = st.slider("Maximum attempts", min_value=3, max_value=40, value=10,
                                   help="Each attempt costs about 4 model calls.")
        target_accepted = st.slider("Stop after N ACTIVE candidates", min_value=1, max_value=5, value=2)
        allow_new_physics = st.checkbox("Allow postulating NEW physical quantities / laws", value=True,
                                        help="Postulates must declare SI dimensions, a coupling and when they reduce "
                                             "to known physics. Each one costs 10% viability.")
        use_requirements = st.checkbox("Decompose the goal into physical requirements first", value=True,
                                       help="The model lists the conditions physics demands; each attempt targets one of them, "
                                            "so predictions measure something that matters. Costs 1-2 extra model calls.")
        user_requirements = st.text_area(
            "Your own requirements (optional, one per line)", value="", height=110,
            help="What must be ACHIEVED for the goal to work, each with a number and a unit, e.g. 'Transfer a 1 cm object "
                 "between two points 1 m apart in under 3.3 ns'. If filled, the model does not derive its own.")
        use_rag = st.checkbox("Search arXiv for optional context", value=True,
                              help="Off = ideas come only from the model's own knowledge.")
        seed_value = st.number_input("Random seed (0 = random)", min_value=0, value=0, step=1)
        minutes = st.number_input("Time limit in minutes (0 = none)", min_value=0, value=0, step=5)
    else:
        target_count = st.slider("Number of Hypotheses", min_value=1, max_value=5, value=2,
                                 help="More hypotheses take exponentially more time.")

    run_btn = st.button("🚀 Run", use_container_width=True, type="primary")


def render_discovery_hypothesis(hyp):
    col1, col2 = st.columns([2, 1])
    with col1:
        icon = "🟢" if hyp.status == "active" else "🔴"
        st.subheader(f"{icon} {hyp.title or hyp.family}  —  {hyp.status.upper()}")
        if hyp.target:
            st.caption(f"🎯 Target requirement: {hyp.target}")
        st.caption(f"strategy: {hyp.strategy} | family: {hyp.family}"
                   + (f" | seeds: {' + '.join(hyp.concepts)}" if hyp.concepts else ""))
        st.markdown(hyp.description)
        if hyp.citations:
            st.markdown("**📚 Literature Citations:**")
            for cit in hyp.citations:
                st.caption(f"- {cit}")
    with col2:
        st.metric("Viability Score", f"{hyp.feasibility_score * 100:.0f}%")
        if hyp.ai_estimate is not None:
            st.caption(f"AI's own estimate: {hyp.ai_estimate * 100:.0f}%")
        st.markdown("#### 🚨 Audit Panel")
        for label, items, box in (("Verified law violations", hyp.violated_hard_constraints, st.error),
                                  ("Logical flaws (-15% each)", hyp.logical_flaws, st.warning),
                                  ("Arithmetic errors verified by Python (-15% each)", hyp.numeric_flags, st.error),
                                  ("Red flags (-15% each)", hyp.red_flags, st.warning),
                                  ("Postulated new quantities (-10% each)", hyp.postulates, st.info),
                                  ("Unproven assumptions (-5% each)", hyp.assumptions, st.info),
                                  ("Speculative notes", hyp.speculative_notes, st.info)):
            box(f"**{label}:** {len(items)}")
            for item in items:
                st.write(f"- {item}")
        if hyp.confirmation_scores:
            st.caption("Independent confirmation rounds: " + ", ".join(f"{x * 100:.0f}%" for x in hyp.confirmation_scores))
        if hyp.status == "active":
            st.warning("Passed automated screening only. Not validated by experiment; expert review required.")


def render_discovery_run(run):
    result = run.result
    st.success(f"Finished: {result.finished_reason}. {len(result.attempts)} attempt(s), "
               f"{len(result.accepted)} ACTIVE candidate(s).")
    with st.expander("🧠 Deterministic conclusion", expanded=True):
        st.text(run.conclusion)
    if result.requirements:
        with st.expander("🎯 Physical requirements " + ("(supplied by you)" if result.requirements_source == "user" else "derived from the goal (model-derived, unverified)"), expanded=False):
            st.dataframe(result.requirement_coverage(), use_container_width=True)

    shown = result.accepted or result.near_misses(3)
    st.markdown("### 🧬 Candidates" if result.accepted else "### 🧬 Closest attempts (none passed the screening)")
    if shown:
        tabs = st.tabs([f"#{i + 1} {h.title[:28] or h.family[:28]}" for i, h in enumerate(shown)])
        for tab, hyp in zip(tabs, shown):
            with tab:
                render_discovery_hypothesis(hyp)

    with st.expander("🗺️ Exploration map (every attempt)", expanded=False):
        rows = [{**row, "concepts": " + ".join(row["concepts"]),
                 "score": None if row["score"] is None else round(row["score"] * 100)}
                for row in result.exploration_log()]
        st.dataframe(rows, use_container_width=True)

    st.divider()
    col_a, col_b = st.columns(2)
    if run.pdf_path:
        with open(run.pdf_path, "rb") as pdf_file:
            col_a.download_button("📥 Download report (PDF)", pdf_file, file_name=os.path.basename(run.pdf_path),
                                  mime="application/pdf", type="primary", use_container_width=True)
    with open(run.json_path, "rb") as json_file:
        col_b.download_button("📥 Download exploration log (JSON)", json_file,
                              file_name=os.path.basename(run.json_path), mime="application/json",
                              use_container_width=True)


# 4. Main Execution Block
if run_btn:
    if not project_name or not goal_description:
        st.error("⚠️ Please provide both a Project Name and a Goal.")

    elif mode.startswith("🧪"):
        config = DiscoveryConfig(max_iterations=max_iterations, target_count=target_accepted,
                                 allow_new_physics=allow_new_physics, use_requirements=use_requirements,
                                 seed=int(seed_value) or None,
                                 max_minutes=float(minutes) or None)
        with st.status("Exploring...", expanded=True) as status:
            run = run_discovery(project_name, goal_description, config, use_rag=use_rag, on_event=st.write,
                                requirements=[l for l in user_requirements.splitlines() if l.strip()] or None)
            status.update(label="Exploration complete!", state="complete", expanded=False)

        st.session_state["discovery_run"] = run

    else:
        # Visual Loading Spinner with real-time status updates
        with st.status("Initializing HECE Engine...", expanded=True) as status:
            
            st.write("🔍 Interpreting user goal...")
            interpreter = GoalInterpreter()
            analysis = interpreter.analyze(goal_description)

            st.write("📚 Retrieving Scientific Context (ArXiv RAG)...")
            knowledge_engine = KnowledgeEngine()
            context = knowledge_engine.retrieve_context(analysis)

            st.write("🚧 Establishing Scientific Boundaries...")
            constraint_engine = ConstraintEngine()
            boundaries = constraint_engine.process_constraints(analysis, context)

            st.write(f"🤖 Activating Multi-Agent Investigation ({target_count} Hypotheses)...")
            pool = AgentPool()
            orchestrator = InvestigationOrchestrator(pool)
            hypotheses = orchestrator.investigate(analysis, context, boundaries, target_count=target_count)

            st.write("🔬 Running Deterministic Math Simulation...")
            simulation_engine = SimulationEngine()
            evaluated_hypotheses = simulation_engine.evaluate(hypotheses, boundaries)

            st.write("🧠 Synthesizing deep scientific conclusion...")
            deep_conclusion = build_conclusion(pool, evaluated_hypotheses)

            st.write("📑 Publishing Scientific Paper (PDF)...")
            pdf_path = PaperGenerator.generate_pdf(project_name, analysis, context, boundaries, evaluated_hypotheses, deep_conclusion)

            status.update(label="Investigation Complete!", state="complete", expanded=False)

        # 5. RESULTS DASHBOARD (The Audit Panel)
        st.success(f"Pipeline completed! Project **{project_name}** successfully evaluated.")

        # Deep Conclusion
        with st.expander("🧠 Deterministic Conclusion", expanded=True):
            st.text(deep_conclusion)

        st.markdown("### 🧬 Proposed Hypotheses")
        
        # Create interactive tabs for each hypothesis
        tabs = st.tabs([f"Hypothesis {i+1}" for i in range(len(evaluated_hypotheses))])

        for i, hyp in enumerate(evaluated_hypotheses):
            with tabs[i]:
                col1, col2 = st.columns([2, 1])

                with col1:
                    status_color = "🟢" if hyp.status == "active" else "🔴" if hyp.status == "rejected" else "🟡"
                    st.subheader(f"{status_color} Status: {hyp.status.upper()}")
                    st.markdown(hyp.description)
                    
                    if hyp.citations:
                        st.markdown("**📚 Literature Citations:**")
                        for cit in hyp.citations:
                            st.caption(f"- {cit}")

                with col2:
                    st.metric(label="Viability Score", value=f"{hyp.feasibility_score * 100:.0f}%")
                    
                    st.markdown("#### 🚨 Audit Panel")
                    
                    st.error(f"**Verified law violations:** {len(hyp.violated_hard_constraints)}")
                    for flaw in hyp.violated_hard_constraints:
                        st.write(f"- {flaw}")

                    st.warning(f"**Logical Flaws (-15% each):** {len(hyp.logical_flaws)}")
                    for flaw in hyp.logical_flaws:
                        st.write(f"- {flaw}")

                    st.warning(f"**Red flags (-15% each):** {len(hyp.red_flags)}")
                    for flag in hyp.red_flags:
                        st.write(f"- {flag}")

                    st.info(f"**Unproven Assumptions (-5% each):** {len(hyp.assumptions)}")
                    for assump in hyp.assumptions:
                        st.write(f"- {assump}")

        st.divider()
        
        # 6. PDF Download Button
        with open(pdf_path, "rb") as pdf_file:
            st.download_button(
                label="📥 Download Official Scientific Paper (PDF)",
                data=pdf_file,
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )

# 7. Persisted results (the page reruns after a download click; keep showing the last discovery run)
if mode.startswith("🧪") and "discovery_run" in st.session_state:
    render_discovery_run(st.session_state["discovery_run"])
