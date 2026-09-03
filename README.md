# LLM-Assisted Clinical Codelist Generation

Pipeline code for an MSc dissertation testing whether large language models can
generate clinical codelists (SNOMED-CT) that approximate a published gold
standard, and how that ability depends on retrieval-augmented generation,
prompting strategy, model type, and the clinical condition being coded.

Seven models (two commercial families, one open-weight biomedical family) were
run against seven clinical conditions, under three prompting strategies
(zero-shot, few-shot, chain-of-thought), with and without retrieval, three
repetitions each, for 882 samples in total. Generated codelists were scored
against NHS Digital Primary Care Domain Reference Sets using precision,
recall, and F1, with every missed code attributed to a retrieval failure or a
generation failure, and every generated code checked against the terminology
for fabrication.

The dissertation text itself is not in this repository. This repo contains
the pipeline, the code that runs the experiments, evaluates the output, and
derives the results tables and figures.

## What's here

- `pipeline_core.py`: shared configuration, the hybrid retrieval stack
  (dense + sparse, combined by reciprocal rank fusion), the three prompt
  builders, gold-standard loading, and the model-call logic.
- `inspect_pipeline.py`: the primary experiment harness, built on
  [Inspect AI](https://github.com/UKGovernmentBEIS/inspect_ai). Runs the full
  factorial design and derives per-epoch, pooled, code-breakdown, and
  retrieval-attribution CSVs from the resulting evaluation logs.
- `experiment_runner.py`: an earlier, checkpointed JSON-file-based runner,
  kept for reference. `inspect_pipeline.py` is the one actually used for the
  reported results.
- `evaluate.py`: precision/recall/F1 computation and CSV derivation for
  `experiment_runner.py`'s output.
- `build_bm25_index.py`: builds the BM25 sparse-retrieval index over the
  SNOMED-CT corpus.
- `categorise_gold_standards.py`: assigns each gold-standard code to one of
  seven descriptive categories (diagnosis, subtype, complication, etc.).
- `enrich_attribution.py`, `check_chd_retrieval.py`, `check_run_health.py`,
  `audit_fabricated_codes.py`, `compute_hallucination_rate.py`,
  `derive_csvs_only.py`, `generate_analysis_report.py`: standalone analysis
  and diagnostic scripts, each documented at the top of the file.
- `notebooks/`: exploratory notebooks for SNOMED-CT preprocessing and early
  retrieval experimentation.
- `inspect_results/`: the derived CSVs (per-epoch, pooled, code-breakdown,
  retrieval-attribution, subtype recall) for every model reported.
- `inspect_logs/`: the raw Inspect AI evaluation logs the above CSVs were
  derived from, for full transparency.
- `outputs/`: supplementary analysis outputs (the fabrication audit sample,
  the CHD retrieval diagnosis, the clinical plausibility review sample).

## Data not included

This pipeline runs against SNOMED-CT (International and UK editions) and NHS
Digital's Primary Care Domain Reference Sets. Neither is included here.
Both are licensed and must be obtained separately:

- SNOMED-CT: via [NHS TRUD](https://isd.digital.nhs.uk/trud), which requires
  its own free registration and license acceptance.
- NHS Digital Primary Care Domain Reference Sets: via the
  [Primary Care Domain Reference Set Portal](https://digital.nhs.uk/data-and-information/data-collections-and-data-sets/data-collections/quality-and-outcomes-framework-qof/quality-and-outcome-framework-qof-business-rules/primary-care-domain-reference-set-portal).

`notebooks/02_snomed_preprocessing.ipynb` documents how the raw SNOMED-CT release
files were turned into the retrieval corpus (a ChromaDB collection plus a
BM25 index) once obtained.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your own API keys
```

Model access (OpenAI, Google, and/or a local Ollama install for the
open-weight models) is configured via the `MODELS` list in `pipeline_core.py`.

## Reproducing a run

```bash
python inspect_pipeline.py
```

This runs the full factorial design against whichever models are enabled in
`pipeline_core.py`'s `MODELS` list, and writes evaluation logs to
`inspect_logs/`. Run `derive_csvs_only.py` to regenerate the summary CSVs from
an existing log without re-running the experiment.

## License

The code in this repository is released under the MIT license (see
`LICENSE`). This does not extend to the SNOMED-CT terminology or the NHS
Digital reference sets, which remain subject to their own licenses.
