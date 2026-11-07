# Screening benchmark results

`hece-benchmark` scores fixed hypotheses whose verdict is known in advance through the same Critic + Synthesizer + SimulationEngine as `run_hece`, without literature retrieval. The question it answers: **does the screening accept sound ideas and stop ideas that break a known law?** Stopping a law-breaking idea matters most for HECE's goal.

Hardware for every run: GTX 1660 SUPER (6 GB), Ollama, one run per row (the model is sampled, so rows move by a case or two between runs).

## Cases

- [`screening.json`](screening.json): 10 cases (5 sound, 5 law-breaking). Written together with the current red flags, so it is **not** an unbiased test.
- [`heldout.json`](heldout.json): 12 cases (6 sound, 6 law-breaking) in new domains, written after the filter and committed before their first run (commit `ea9e649`). Violations avoid the red-flag trigger words; sound cases include wording a naive filter would wrongly flag. The filter has not been tuned to them.

## Results (2026-11-07)

| Model | Cases | Sound accepted | Law-breaking accepted |
| --- | --- | --- | --- |
| `llama3` 8B, before the fixes below | screening | 1 / 5 | 0 / 5 |
| `llama3` 8B | screening | 4 / 5 | 0 / 5 |
| `llama3` 8B | **held-out** | 1 / 6 | **3 / 6** |
| `qwen3:4b-instruct-2507` | screening | 3 / 5 | 0 / 5 |
| `qwen3:4b-instruct-2507` | **held-out** | 2 / 6 | **0 / 6** |

What the numbers say:

- **The good `llama3` result on the screening set did not generalise.** On held-out cases it accepted a wind turbine above the Betz limit, a catalyst that "pushes past equilibrium" and a closed-loop water wheel (perpetual motion without the trigger words), each at 75%.
- **`qwen3:4b-instruct-2507` let no law-breaking case through (0 of 11)**, rating them 0 to 35% itself, and runs about 3 times faster fully on a 6 GB GPU. It is also stricter with sound ideas (5 of 11 accepted), mostly because it lists many assumptions (-5% each). It is the default model since this measurement.
- Python checks carry real weight: an engine above the Carnot limit was rated 90% by `llama3` and stopped by the arithmetic check in `lawchecks.py`.
- The score alone rarely separates the groups. What keeps law-breaking ideas out is the combination of verified violations, law-level red flags and the judge model.

Fixes measured by the first two rows: unverified accusations no longer lower the score (they had sunk 4 of 5 sound cases), the Carnot check, and law-level red flags that block acceptance.

## Known gaps (not fixed, on purpose)

Checks that would have caught the held-out failures (Betz limit, refrigeration COP above Carnot, Landauer limit, catalysts and equilibrium) are natural next steps, but adding them after seeing these cases would contaminate the held-out set. They should be added together with a **new** held-out set.

## Reproduce

```bash
hece-benchmark                                   # screening.json with the model in MODEL_NAME
hece-benchmark --cases benchmarks/heldout.json
MODEL_NAME=llama3 hece-benchmark --repeat 3      # compare models, average out sampling noise
```
