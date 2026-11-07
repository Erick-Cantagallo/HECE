<div align="center">

<img src="docs/assets/banner.svg" alt="HECE, the Hypothesis & Creativity Engine. Version 1.0, research prototype." width="100%">

<br>

![Version 1.0](https://img.shields.io/badge/version-1.0-4ade80?labelColor=052e16)
![Status: research prototype](https://img.shields.io/badge/status-research%20prototype-facc15?labelColor=1c1917)
[![CI](https://github.com/Erick-Cantagallo/HECE/actions/workflows/ci.yml/badge.svg)](https://github.com/Erick-Cantagallo/HECE/actions/workflows/ci.yml)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-3776AB?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-22c55e)

**An engine for creative hypotheses that can be tested and that respect the laws we know.**

</div>

> 🔬 **Version 1.0, research prototype.** HECE runs end to end on a normal PC with a local model: it reads the literature, proposes mechanisms, attacks them, checks the attacks in Python and writes a report. It is a long-term project and a lot is still ahead, so do not read anything it produces as established science.

## The idea

HECE (Hypothesis & Creativity Engine) is meant to generate **creative hypotheses** that can be **tested** and that **do not violate the laws of nature as we know them today**.

The interesting case is the idea that *would* break a known law. HECE should neither throw it away nor pretend the law is not there. It should look for an alternative path: create something new first (a new model, a new assumption or a missing technology, for example) and only then go beyond the law.

> HECE does not exist to answer impossible questions.
>
> HECE exists to systematically explore what would be required to transform impossible ideas into scientifically plausible possibilities.
>
> From the [constitution](docs/constitution.md)

HECE is not a chatbot, a search engine or an oracle. Sometimes the right outcome is "current science cannot answer this" (see the [project identity](docs/PROJECT_IDENTITY.md)).

## Where it is today

HECE has two modes that share the same building blocks ([architecture](docs/architecture.md)). The **classic investigation** runs this pipeline:

1. **Goal interpretation** (deterministic, no LLM): keywords, domain, complexity and simple constraints (such as "without" and "only") taken from a goal written in English.
2. **Knowledge**: a few built-in laws for physics and biology, plus real papers fetched from arXiv (RAG).
3. **Constraints**: hard rules (laws and strict requirements) kept apart from preferences.
4. **Hypothesis generation**: three agents running on a local LLM through [Ollama](https://ollama.com). An expert proposes, a critic attacks, a synthesizer consolidates.
5. **Scoring**: a fixed formula over the violations, flaws and assumptions that the agents reported. Accusations are only counted when Python can verify the quoted text, and only candidates with no verified law violation and at least 65% are kept.
6. **Report**: a PDF in `reports/`.

The **inventor mode** ([discovery engine](docs/DISCOVERY_ENGINE.md)): instead of a fixed number of hypotheses, it keeps trying different mechanisms for a goal (explore, recombine unrelated concepts, refine near-misses), remembers what failed and why, and after repeated failures may postulate a new physical quantity, which must declare SI dimensions, an equation and when it reduces to known physics. Every attempt is logged in `runs/`.

**When an idea runs into a law**, inventor mode does not just drop it: a REROUTE attempt must reach the same effect while keeping the law (pay the cost the law demands, rely on a technology that does not exist yet, or change the condition the limit depends on). The report then lists **what would have to be invented first**, each item with a numeric specification.

**Measuring the filter.** `hece-benchmark` scores hypotheses whose verdict is known in advance, including 12 held-out cases written after the filter. With the default model (`qwen3:4b-instruct-2507`) no law-breaking case got through (0 of 11), while only about half of the sound ones were accepted; `llama3` let 3 of 6 held-out violations through. Details and caveats: [benchmarks/RESULTS.md](benchmarks/RESULTS.md).

**Not there yet:**

- **A proven creative core.** Inventor mode is a first attempt at the idea above (finding a way around a barrier by creating something new first), but it has not been validated: whether its candidates are any good still depends on the model and needs human review.
- **Testing hypotheses.** The score does not simulate anything. It counts the problems reported by the agents, so it is only as good as the model behind them.
- **Laws for other domains.** Only physics and biology have built-in laws, plus a few universal limits (see the [roadmap](ROADMAP.md)).
- **Any guarantee of scientific correctness.** Treat the output as brainstorming that needs human review.

Known quirk: the PDF uses built-in fonts. Greek letters, superscripts and typographic quotes are transliterated (`μ`, `m^2`, `'`), but other characters outside Latin-1 still show up as `?`.

## What a run looks like

These are real, unedited runs on a desktop GPU (full write-up in [examples/](examples/)):

```text
$ hece "How could a battery store more energy per kilogram?" -p "Battery Energy Density" -n 1
   === Monte Carlo Attempt 2/4 ===
    -> [Expert] Inventing hypothesis based on the literature...
    -> [Critic] Judging the invention against the literature...
    -> [Critic] Checking internal consistency...
    -> [Synthesizer] Classifying and assigning AI Viability Score...
   📊 [Simulation] Score: 20% | Broken Laws: 0
   ❌ [REJECTED]: AI estimate 80% -> final 20% after penalties (logical flaws: 1, assumptions: 2,
      unverified accusations: 2, red flags: 1, numeric errors: 0); below the 65% threshold.
```

From the PDF of the same run:

```text
Red flags (deterministic screen): perpetual motion / over-unity / free energy: 'perpetual'
```

The model rated its own idea 80%. Python found a grounded logical flaw, a "perpetual motion" pattern and two unproven assumptions, and rejected it. In [inventor mode](examples/inventor-desalination/), an idea that reached exactly 65% was re-assessed twice independently (45%, 15%) and rejected rather than reported as a success.

| | Classic (`-n 1`) | Inventor (6 attempts) |
| --- | --- | --- |
| Time on a GTX 1660 SUPER, `llama3` 8B | ~6.5 min | ~12 min |
| Output | [PDF](examples/classic-battery/report.pdf) | [PDF](examples/inventor-desalination/report.pdf) + [JSON log](examples/inventor-desalination/exploration-log.json) |

## Try it

You need Python 3.10 or newer and [Ollama](https://ollama.com/download) running with a model pulled (the default is `qwen3:4b-instruct-2507-q4_K_M`, 2.5 GB, chosen with the benchmark; it fits fully on a 6 GB GPU). Other Ollama models work through `MODEL_NAME`, for example `llama3` (5 GB, slower, and it let more law-breaking ideas through). The model changes the results a lot.

```bash
ollama pull qwen3:4b-instruct-2507-q4_K_M

git clone https://github.com/Erick-Cantagallo/HECE.git
cd HECE
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e .

hece "Can quantum sensors detect dark matter?" -p Orion -n 2
```

- Without arguments, `hece` asks for the project name, the goal and the number of hypotheses. `python -m hece` does the same.
- Write the goal in English: the deterministic interpreter only knows English keywords.
- More hypotheses mean more calls to the model, so more time.
- If Ollama is not running or the model is missing, HECE stops right away with a message that says how to fix it.
- Inventor mode: `hece-discover "reduce the energy consumption of seawater desalination" --iterations 12` (or `python -m hece.discover`). Options are listed in `hece-discover --help` and in the [discovery engine](docs/DISCOVERY_ENGINE.md) page.
- Web interface: `pip install -e ".[app]"` and then `streamlit run app.py`.
- Optional settings live in `.env` (copy `.env.example`): `MODEL_NAME` (default `qwen3:4b-instruct-2507-q4_K_M`) and `MAX_RETRIES` (default `3`, how many times the synthesizer retries a malformed JSON answer).
- Inference is local. The only network call is the arXiv search.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

The tests need no Ollama, internet or GPU: the LLM and arXiv are mocked. The [CI](.github/workflows/ci.yml) runs them on Python 3.10 to 3.13.

## Documentation

- Why and what: [vision](docs/vision.md), [project identity](docs/PROJECT_IDENTITY.md), [constitution](docs/constitution.md), [philosophy](docs/philosophy.md), [glossary](docs/glossary.md)
- How: [current architecture](docs/architecture.md), [specifications](docs/specifications/)
- Where it is going: [roadmap](ROADMAP.md), [changelog](CHANGELOG.md)

## Contributing

Ideas and feedback are welcome. Please read [CONTRIBUTING.md](CONTRIBUTING.md) and the [code of conduct](CODE_OF_CONDUCT.md). To cite the project, use the "Cite this repository" button on GitHub ([CITATION.cff](CITATION.cff)). Licensed under the [MIT License](LICENSE).

<div align="center">
<sub><i>"Curiosity deserves methodology."</i></sub>
</div>
