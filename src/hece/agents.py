# HECE/src/hece/agents.py
import os
import json
import re
import uuid
from textwrap import shorten
from typing import List, Any, Optional
from hece.inference import DEFAULT_MODEL, InferenceEngine
from hece.verification import split_violations, verified_evidence, filter_citations, parse_flaws, resolve_numbered_refs, drop_goal_restatements, split_law_flaws
from hece.core.models.base import Hypothesis, GoalAnalysis, KnowledgeContext, ConstraintContext

def _ensure_list(value: Any) -> List[str]:
    """Ensures that the LLM output is always a list of strings, preventing Pydantic ValidationErrors."""
    if isinstance(value, list):
        raw_list = [str(v) for v in value]
    elif isinstance(value, str):
        raw_list = [value]
    else:
        raw_list = []
        
    ignore_words = ["none", "none.", "n/a", "nil", "nothing", "empty", "no", "false"]
    null_like = re.compile(
        r"^(?:none|n/a|nil|nothing|not applicable)\b.*$"
        r"|^(?:there (?:is|are) )?no (?:\w+ ){0,2}(?:contradictions?|flaws?|errors?|issues?|problems?|violations?|inconsisten\w+)(?: \w+){0,3}\.?$",
        re.I)
    clean_list = [item for item in raw_list
                  if item.strip() and re.search(r"\w", item) and item.strip().lower() not in ignore_words
                  and not null_like.match(item.strip())]
    
    return clean_list

DEFAULT_MAX_RETRIES = 3

def _max_retries() -> int:
    """How many times the Synthesizer may retry malformed JSON (env MAX_RETRIES, default 3)."""
    try:
        return max(1, int(os.getenv("MAX_RETRIES", DEFAULT_MAX_RETRIES)))
    except ValueError:
        return DEFAULT_MAX_RETRIES

def build_book(context: KnowledgeContext) -> str:
    """The shared context ('THE BOOK') handed to every agent."""
    return f"KNOWN FACTS: {' | '.join(context.known_facts)}\nLAWS: {' | '.join(context.domain_laws)}"

class Agent:
    def __init__(self, name: str, role_description: str):
        self.name = name
        self.role = role_description
        self.inference = InferenceEngine(model_name=os.getenv("MODEL_NAME", DEFAULT_MODEL))

    def perform_task(self, task: str, context: str, creative: bool = False, temperature: Optional[float] = None) -> str:
        if creative:
            # Inventor mode: the model may go beyond the context, but must follow the output format.
            prompt = f"""
        You are {self.name}. Your role is: {self.role}
        
        BACKGROUND (laws and any retrieved literature): {context}
        
        TASK: {task}
        """
        else:
            prompt = f"""
        You are {self.name}. Your role is: {self.role}
        
        CONTEXT (THE BOOK): {context}
        
        TASK: {task}
        
        Provide a concise, expert-level response based ONLY on the context provided and scientific laws.
        """
        if temperature is not None:
            return self.inference.ask(prompt, temperature=temperature)
        return self.inference.ask(prompt)

class AgentPool:
    def __init__(self):
        self.expert = Agent("ScientificExpert", "You propose highly detailed scientific hypotheses.")
        self.inventor = Agent(
            "Inventor",
            "You are an inventor-scientist. You combine unrelated ideas from science, nature and engineering into "
            "new mechanisms that respect the listed laws. You never claim that an idea works: you state a measurable "
            "prediction and what result would prove it wrong.")
        self.critic = Agent("ScientificCritic", "You objectively judge hypotheses against real-world scientific literature and absolute physics constraints.")
        self.synthesizer = Agent("Synthesizer", "You structure scientific critiques into rigid JSON architectures.")
        self.writer = Agent("ScientificWriter", "You write clear plain-prose scientific summaries.")

class InvestigationOrchestrator:
    def __init__(self, pool: AgentPool):
        self.pool = pool

    JUDGE_TEMPERATURE = 0.1   # judges must be consistent: the same idea should not get 0 flaws once and 5 the next time

    def _synthesize(self, raw_hypothesis: str, critique: str, temperature: Optional[float] = None) -> Optional[dict]:
        """Synthesizer call with up to MAX_RETRIES attempts (default 3). Returns the parsed JSON dict (with a score) or None."""
        max_retries = _max_retries()
        error_feedback = ""
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                print(f"       [Retry {attempt}/{max_retries}] Correcting JSON format...")

            task_synth = f"""
                Original Hypothesis: {raw_hypothesis}
                Critic's Judgment: {critique}
                
                TASK: Extract the structured fields below from the hypothesis and the Critic's judgment, and assign a realistic 'ai_viability_score' (0.0 to 1.0). Do NOT rewrite the hypothesis.
                """

            # Explicitly instructing the Synthesizer how to handle "NO LAWS BROKEN".
            json_format = f"""
                CRITICAL INSTRUCTION: Return ONLY a valid JSON object.
                
                FIELD INSTRUCTIONS:
                - "assumptions": List unproven assumptions. 
                - "required_conditions": List conditions needed.
                - "violated_hard_constraints": ONLY copy violations the Critic proved with LAW, QUOTE and MECHANISM. Copy them verbatim. If the Critic said "NO LAWS BROKEN", this array MUST BE EMPTY [].
                - "citations": List the references used.
                - "ai_viability_score": A float between 0.0 and 1.0 representing the AI's estimation of feasibility.
                
                JSON SCHEMA REQUIRED:
                {{
                    "assumptions": ["string"],
                    "required_conditions": ["string"],
                    "violated_hard_constraints": [{{"law": "string", "quote": "string", "mechanism": "string"}}],
                    "citations": ["string"],
                    "ai_viability_score": 0.0
                }}
                {error_feedback}
                """

            final_output = self.pool.synthesizer.perform_task(task_synth, json_format,
                                                               temperature=temperature if temperature is not None else self.JUDGE_TEMPERATURE)

            try:
                start_idx = final_output.find('{')
                end_idx = final_output.rfind('}')
                if start_idx == -1 or end_idx == -1 or end_idx <= start_idx:
                    raise ValueError("Invalid JSON format.")

                clean_json = final_output[start_idx:end_idx+1]
                try:
                    data = json.loads(clean_json, strict=False)
                except json.JSONDecodeError:
                    clean_json = clean_json.replace('\\', '\\\\').replace('\n', ' ')
                    data = json.loads(clean_json, strict=False)

                if "ai_viability_score" not in data:
                    raise ValueError("Missing 'ai_viability_score'.")  # triggers a retry instead of a silent 0.0
                data["ai_viability_score"] = min(1.0, max(0.0, float(data["ai_viability_score"])))
                return data
            except Exception as e:
                error_feedback = f"\nERROR: Fix JSON formatting. Reason: {str(e)}"
        return None

    def assess(self, raw_hypothesis: str, analysis: GoalAnalysis, context: KnowledgeContext,
               boundaries: ConstraintContext, speculative: bool = False, target: str = "",
               judge_temperature: Optional[float] = None) -> Optional[Hypothesis]:
        """
        Critic (laws) + Critic (internal flaws) + Synthesizer (JSON) for ONE hypothesis text.
        Returns an un-evaluated Hypothesis (status 'speculative'), or None if the Synthesizer collapsed.
        `speculative=True` tells the Critic that postulating NEW quantities/laws is allowed by design.
        `target` is the physical requirement the hypothesis claims to address (inventor mode).
        """
        the_book = build_book(context)
        judge = judge_temperature if judge_temperature is not None else self.JUDGE_TEMPERATURE

        print("    -> [Critic] Judging the invention against the literature...")
        # Anti-Hallucination Prompting: force the SLM to be objective, not sycophantic.
        speculative_note = ""
        if speculative:
            speculative_note = (
                "\n            NOTE: This idea may postulate a NEW physical quantity or law on purpose. Do not report a violation "
                "just because something is new. Report a violation only if the mechanism contradicts a listed law "
                "(for example it creates net energy) or contradicts the postulate's own 'reduces to known physics' condition.\n")
        task_critic = f"""
            Review this hypothesis: {raw_hypothesis}

            CHECKLIST OF LAWS: {boundaries.hard_constraints}
            {speculative_note}
            Most hypotheses violate NONE of these laws. Ignore any law that is not relevant.
            Report a violation ONLY if you can provide all three items:
            LAW: copy the law text exactly from the checklist.
            QUOTE: copy at least 4 consecutive words from the hypothesis that break it.
            MECHANISM: explain in at least 15 words why that quote breaks the law.
            If you cannot provide all three, answer exactly: NO LAWS BROKEN.
            """
        critique = self.pool.critic.perform_task(task_critic, the_book, temperature=judge)

        print("    -> [Critic] Checking internal consistency...")
        extra_flaw = (" (4) a PREDICTION that known physics would also make, so it cannot tell the idea apart; "
                      "(6) a setup that could not be built in a laboratory (for example one that needs a star or a black hole).") if speculative else ""
        target_flaw = ""
        if target:
            target_flaw = (f" (5) the PREDICTION would not show that the TARGET REQUIREMENT is met even if it were observed; "
                           f"(7) the mechanism assumes as a given ingredient the very thing the TARGET REQUIREMENT asks to achieve (circular)."
                           f"\n            TARGET REQUIREMENT: {target}")
        task_flaws = f"""
            Review this hypothesis for INTERNAL logical problems only: {raw_hypothesis}

            Look for: (1) statements that contradict each other, (2) a mechanism step that is asserted
            without any physical explanation, (3) a claim that contradicts a law the text itself cites.{extra_flaw}{target_flaw}
            Most hypotheses have between 0 and 3 real problems. Do not invent problems.
            For each problem write ONE line in exactly this format:
            FLAW: <one sentence> | QUOTE: <at least 4 consecutive words copied from the hypothesis>
            If there are none, answer exactly: NO FLAWS
            """
        flaw_review = self.pool.critic.perform_task(task_flaws, the_book, temperature=judge)
        # only flaws whose quote exists in the text; flaws that accuse a physical law are law accusations
        flaws, law_flaws = split_law_flaws(parse_flaws(flaw_review, raw_hypothesis))

        print("    -> [Synthesizer] Classifying and assigning AI Viability Score...")
        data = self._synthesize(raw_hypothesis, critique, judge)
        if data is None:
            print("[ERROR] Assessment failed: the Synthesizer could not produce valid JSON.")
            return None

        description = raw_hypothesis.strip()  # the Expert text itself, never rewritten by the Synthesizer
        claims = data.get("violated_hard_constraints", [])
        claim_text = f"{raw_hypothesis} {description}"
        verified, unverified = split_violations(claims, claim_text, boundaries.hard_constraints)
        evidence = verified_evidence(claims, claim_text, boundaries.hard_constraints)
        unverified = unverified + [f"(law cited in the flaw review, not verified) {shorten(f.split(' (quote:')[0], 200, placeholder='...')}" for f in law_flaws]

        notes: List[str] = []
        if not verified and len(unverified) >= 3:
            # The Critic accused (almost) every law without proof: its mood must not set the score.
            redo = self._synthesize(raw_hypothesis, "NO LAWS BROKEN. (The Critic's earlier accusations could not be verified and were discarded.)", judge)
            if redo is not None:
                notes.append(f"AI estimate recomputed: {len(unverified)} law accusations could not be verified and were discarded")
                data = redo

        ai_score = data["ai_viability_score"]
        cits = filter_citations(_ensure_list(data.get("citations", [])), the_book)
        for ref in resolve_numbered_refs(description, the_book):
            if ref not in cits:
                cits.append(ref)
        return Hypothesis(
            id=str(uuid.uuid4()),
            goal_id=analysis.goal.id,
            description=description,
            assumptions=drop_goal_restatements(_ensure_list(data.get("assumptions", [])), analysis.goal.description),
            required_conditions=_ensure_list(data.get("required_conditions", [])),
            violated_hard_constraints=verified,
            violation_evidence=evidence,
            unverified_violations=unverified,
            needs_human_review=bool(unverified or verified),
            logical_flaws=flaws,
            citations=cits,
            speculative_notes=notes,
            feasibility_score=ai_score,
            ai_estimate=ai_score,
            confidence=0.5,
            status="speculative"
        )

    def investigate(self, analysis: GoalAnalysis, context: KnowledgeContext, boundaries: ConstraintContext, target_count: int = 2) -> List[Hypothesis]:
        hypotheses = []
        generated_ideas = []  
        
        the_book = build_book(context)
        
        for i in range(target_count):
            print(f"\n   [Iteration {i+1}]")
            
            print("    -> [Expert] Inventing hypothesis based on the literature...")
            avoid_prompt = f" Make it completely DIFFERENT from these previous ideas: {generated_ideas}" if generated_ideas else ""
            task_propose = f"Propose a detailed hypothesis for: {analysis.goal.description}. Start directly with the hypothesis title: no greetings and no comments about the task. Do not list or restate the scientific laws; mention a law only where your mechanism directly depends on it.{avoid_prompt}"
            raw_hypothesis = self.pool.expert.perform_task(task_propose, the_book)

            agent_hypothesis = self.assess(raw_hypothesis, analysis, context, boundaries)
            if agent_hypothesis is None:
                print(f"[ERROR] Iteration {i+1} failed.")
                continue
            hypotheses.append(agent_hypothesis)
            generated_ideas.append(agent_hypothesis.description[:100])
                        
        return hypotheses
