# Example runs

Two unedited runs of HECE 1.0 on an ordinary desktop: `llama3` (8B) through Ollama on a GTX 1660 SUPER (6 GB VRAM, about 78% of the model on the GPU), with live arXiv retrieval. Nothing was cherry-picked or retouched. These are the first full runs with a real model.

In both runs **no hypothesis passed** the 65% screening. That is the expected behaviour with an 8B model, not a failure: the point of HECE is that the language model only *proposes*, and Python decides what counts. Each folder shows what the model proposed, which problems were proven against the text, and why every idea was rejected.

## Classic investigation: battery energy density

```bash
hece "How could a battery store more energy per kilogram?" -p "Battery Energy Density" -n 1
```

[report.pdf](classic-battery/report.pdf) · [console.log](classic-battery/console.log) · 4 attempts, about 6.5 minutes

What to look at in the report:

- **Hypothesis 2** describes a "perpetual motion-like effect". The deterministic red-flag screen caught the pattern (`perpetual motion / over-unity / free energy`) and cost it 15%.
- **Hypothesis 3** proposes tapping "the zero-point energy of the quantum vacuum" through entanglement. It was flagged as `entanglement used as energy storage or transfer`.
- The Critic's law accusations that could not be tied to a real quote are listed as **unverified, not applied**. They are shown to the reader but do not change the score.
- Every logical flaw carries the exact quote from the hypothesis that it refers to.

## Inventor mode: seawater desalination

```bash
hece-discover "reduce the energy consumption of seawater desalination" --name RealDiscovery1 --iterations 6 --target 1 --seed 7
```

[report.pdf](inventor-desalination/report.pdf) · [exploration-log.json](inventor-desalination/exploration-log.json) · [console.log](inventor-desalination/console.log) · 6 attempts, about 12 minutes

What to look at:

- **Requirements.** The model split the goal into 4 measurable requirements (R1 to R4), and each attempt targets one of them. They are labelled *model-derived, not verified*, and some are questionable, which is why you can supply your own with `--requirement`.
- **Winner's curse check.** Attempt 1 scored 65% in its first assessment, which is exactly the threshold. Two independent re-assessments gave 45% and 15%, so it was rejected instead of being reported as a success.
- **Strategies.** The engine chose explore, recombine and postulate by itself. Recombination forced unrelated seeds together (for example *tardigrade damage-suppressor protein + cryogenic temperature near 4 K + hierarchical structuring*).
- **Postulate.** After 3 failures in a row, attempt 4 postulated a new quantity, *Phonon-Induced Thermal Conductance*, with SI dimensions, an equation, a magnitude and the condition under which it reduces to known physics. The dimensional check noticed that its units match entropy or heat capacity, and the report shows the difference the postulate had to declare for that case.
- The **exploration map** (section 5 of the report, and the JSON log) records every attempt with its strategy, target and the barrier that stopped it.

## Reproducing

Results change from run to run: the model is sampled, and the arXiv results change over time. `--seed` makes the strategy choices and concept sampling reproducible, but not the model's text. To compare models, set `MODEL_NAME` in `.env` (for example `qwen3:4b-instruct-2507-q4_K_M`).
