# HECE Discovery Engine (inventor mode)

Inventor mode turns HECE from "evaluate N hypotheses" into an **explorer**: it keeps trying different
mechanisms for a goal, remembers what failed and why, and never repeats itself.

## How to run

```
streamlit run app.py                                   # choose "Discovery (inventor)" in the sidebar
python -m hece.discover "reduce the energy consumption of seawater desalination" --iterations 12 --target 2
python -m hece.discover "your goal" --seed 7 --no-rag --no-new-physics --minutes 30
```

Outputs: a PDF report (`reports/`) and a full exploration log (`runs/*.json`, rewritten after every attempt).

## Step 0: requirements (decomposition)

You can write the requirements yourself (sidebar text area, or `--requirement "..."` repeated on the CLI). That is the most
reliable option: the model is then not asked to derive any. Good requirements are EFFECTS to achieve with a number and a
unit, e.g. "Move a 1 cm object between two points 1 m apart in under 3.3 ns". Limits that must not be broken (speed of light,
conservation, entropy) are NOT requirements: they are checked as laws.

If you do not provide any, the model derives them and Python screens the answer: each needs a numeric target, must not
be a "must not exceed" limit and must not restate a listed law; rejected lines are fed back with the reason, one retry,
then the run continues without requirements.

Before exploring, the model is asked which physical conditions MUST hold for the goal to work (3-4 measurable
statements, e.g. "sustain a negative energy density of X J/m^3 in 1 cm^3"). They are model-derived and unverified.
Each attempt targets ONE requirement (open ones first; a refinement keeps its parent's target), and the PREDICTION must
measure that requirement. The run ends early when every requirement has an ACTIVE candidate.
An ACTIVE candidate for one requirement does NOT achieve the goal: the goal needs all of them at once.
Disable with `use_requirements=False` (sidebar checkbox in the app).

## The loop

Each iteration the engine (deterministically, in Python) picks one strategy:

| Strategy    | What the Inventor agent is asked to do |
|-------------|-----------------------------------------|
| `explore`   | Invent a mechanism from a family that is not in the "already tried" list. |
| `recombine` | Build a mechanism out of 2-3 unrelated seed concepts sampled from `concepts.py` (materials, organisms, phenomena, conditions, principles). |
| `refine`    | Take the best near-miss (score >= 40%) and fix only its recorded problems (x -> x1). A parent is refined at most twice. |
| `postulate` | After 3 consecutive failures, remove a recorded barrier by postulating a NEW physical quantity or law. This is the ONLY strategy where new quantities are allowed (and it must contain one). |

Schedule: attempt 1 = explore; odd attempts = recombine; every third attempt = refine when a near-miss exists;
every fourth attempt = postulate when allowed and 3+ attempts in a row failed.

## What a candidate must contain

The Inventor answers in labelled lines (not JSON, which small models break). Python parses and validates them:

```
TITLE / FAMILY / MECHANISM (>= 30 words, with numbers)
NEW QUANTITY: name | SYMBOL | DIMENSIONS | DEFINITION | EQUATION | MAGNITUDE | COUPLING | REDUCES TO KNOWN PHYSICS WHEN
              | DIFFERS FROM KNOWN QUANTITY BY (only when the dimensions equal a known quantity)   (POSTULATE attempts only)
PREDICTION   (>= 8 words and a number)
REFUTATION   (>= 8 words)
```

* Invalid format -> one retry with feedback, then the attempt is logged as `invalid`.
* Novelty filter: same family, or keyword similarity >= 0.55 with an earlier attempt -> `duplicate`
  (no model calls are spent assessing it).
* A postulate needs a real equation that uses its symbol and a numeric magnitude/bound with parseable SI units.
* Declared SI dimensions are parsed (`dimensions.py`: handles `kg m2 s-2`, `C^(-2)`, `J (joules)`). Unparseable units
  invalidate the candidate. Dimensions identical to a known quantity (energy, intensity, entropy...) are rejected as
  "a known quantity under a new name" unless `DIFFERS FROM KNOWN QUANTITY BY` explains the difference.

## Scoring (inventor mode)

Same engine as classic mode, plus:

* **Falsifiability Lock**: no prediction or no refutation -> 0%.
* **Postulate cost**: -10% per postulated new quantity (an extra law must earn its place).
* Exotic matter / negative energy is *not* a red flag in this mode (it is legitimate to explore); the other red flags still apply.
* The listed laws (thermodynamics, `c`, conservation, material limits, biology when organisms are involved)
  stay **hard constraints**. A postulate extends physics; it may not contradict these laws or its own
  "reduces to known physics when" condition.

## Judging rules learned from real runs (100 attempts, portal gun)

* **Arithmetic check (`numerics.py`)**: when a candidate writes one quantity twice ("300 m/s, which is 0.01c"), both are
  converted to SI and compared (15% tolerance). Disagreement = verified numeric error, -15% each and human review.
  It only compares quantities of the same dimension and only trusts explicit equivalence wording.
* **Circularity**: a mechanism that assumes a hypothetical ingredient as available ("a shell of negative mass") assumes the hard
  part. In inventor mode this is a red flag (-15%); declaring a new quantity through a POSTULATE attempt is the legitimate route.
  Producing negative energy density by known physics (e.g. Casimir plates) is not flagged.
* **Apparatus needing a star or black hole** and **vague prediction/refutation wording** ("or other means", "any significant
  effect", "etc.") are red flags too. The flaw critic is also asked about circularity and setups that cannot be built in a lab.
* **Confirmation rounds (winner's curse)**: a candidate that reaches the threshold was selected because its noisy judgement
  came out high. Before it is accepted it is re-assessed twice independently (judge temperature 0.5) and must reach the
  threshold every time; the score becomes the minimum. Only would-be ACTIVE candidates pay for this (about 6 model calls).
  Both ACTIVE candidates of the first two real runs sat at exactly 65%, i.e. at the edge of the noise.
* **Scale check**: a prediction that claims a region far larger than every described component (a 1 cm^3 region from parts
  of 1-10 um) with no array or scaling described is a verified numeric error (-15%).
* **Self-contained text**: a candidate that says "as before", "unchanged" or "the earlier design" is invalid and must be
  rewritten in full. 9 of 15 real refinements were diffs, not hypotheses.
* **The model's own estimate is an anchor, not a measurement**: 56% of 116 estimates were exactly 0.8. In practice a
  candidate passes only when the total penalty is at most 15%, so the penalties and confirmations carry the decision.
* **Sound needs a medium**: acoustic/sonic/shock waves "through the vacuum of space" are a red flag.
* A refinement chain is cut after 2 refinements (the model only changed numbers and kept the same score).
* Postulate lines are validated strictly (symbol, equation, numeric magnitude, units). The prompt shows one example line
  and the model gets 2 format retries.

* Critic and Synthesizer run at temperature 0.1 (the same idea used to get 0 flaws once and 5 the next time).
* A "flaw" that accuses a physical law is routed to the law-accusation channel (10%, human review), not counted as a flaw.
* If the Critic accuses 3+ laws and none can be verified, the score is recomputed without the accusations.
* Novelty: siblings of one refinement chain are not duplicates of each other; an unchanged refinement is.
* Measured: the penalty rules were NOT the bottleneck (relaxing all of them would pass 1 of 55). Hand-waving
  ("a bubble of space-time") was. The bar was not lowered.

## ArXiv

Literature is optional. A search that works is cached for 7 days in `.hece_cache/` (delete the folder to refresh).
HTTP 503 is retried (5 s, then 15 s); HTTP 429 (rate limit) is NOT retried: the run continues without literature and the
report says "LITERATURE SEARCH FAILED". Untick the ArXiv box in the app when you do not need it.

## Honesty limits

* ACTIVE (>= 65%, no verified violation, falsifiable) means **worth testing**, never "proven".
* The model's estimate is still an opinion; Python limits the damage but does not calibrate it.
* "Verified" law violations are checked for a real quote and a listed law, not for correct physics: every veto is flagged for human review.
* Without literature (`--no-rag`, or arXiv unavailable) ideas come only from the model's own knowledge and are labelled as ungrounded.
* Finding nothing is a valid result: the exploration map shows what was tried and which barrier stopped each attempt.

## Files

`explorer.py` (loop, strategies, archive) | `candidate.py` (format and validation) | `concepts.py` (seed bank) |
`dimensions.py` (SI units) | `pipeline.py` (shared entry point) | `discover.py` (CLI) | `conclusion.py` (deterministic summary)
