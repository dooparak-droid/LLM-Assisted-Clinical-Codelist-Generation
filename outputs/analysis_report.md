# LLM Codelist Generation — Analysis Report

## Cross-model comparison

Two means are reported per model, deliberately, not one:

- **Best-strategy mean**: for each condition, the single best-performing RAG strategy, averaged across conditions. An optimistic ceiling — what a practitioner gets *if* they already knew which strategy to pick.
- **Overall mean**: every condition x strategy x retrieval_type cell (including non-RAG and the weaker strategies), averaged. The honest expectation over the full experimental design, with no post-hoc strategy selection.

The gap between the two is itself informative — a large gap means strategy/retrieval choice matters a lot for that model; a small gap means the model is robust to it.

### Best RAG strategy mean

| Model | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|
| Gemini-3.1-Flash-Lite | 0.509 | 0.687 | 0.536 | 0.510 | 2.175 |
| Gemini 3.1 Pro | 0.479 | 0.623 | 0.505 | 0.479 | 1.476 |
| GPT-4o (v1 baseline model) | 0.450 | 0.443 | 0.417 | 0.423 | 1.004 |
| GPT-5.4-mini | 0.416 | 0.661 | 0.469 | 0.429 | 2.463 |
| GPT-5.5 | 0.549 | 0.707 | 0.561 | 0.544 | 2.242 |
| MedGemma 1.0-27B | 0.277 | 0.397 | 0.305 | 0.284 | 1.581 |
| MedGemma 1.5-4B | 0.203 | 0.297 | 0.210 | 0.199 | 1.460 |

### Overall mean (all conditions x strategies x retrieval types)

| Model | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|
| Gemini-3.1-Flash-Lite | 0.247 | 0.356 | 0.257 | 0.241 | 1.819 |
| Gemini 3.1 Pro | 0.298 | 0.338 | 0.277 | 0.270 | 1.040 |
| GPT-4o (v1 baseline model) | 0.292 | 0.224 | 0.220 | 0.238 | 0.729 |
| GPT-5.4-mini | 0.268 | 0.363 | 0.257 | 0.246 | 1.775 |
| GPT-5.5 | 0.481 | 0.451 | 0.369 | 0.396 | 1.600 |
| MedGemma 1.0-27B | 0.101 | 0.201 | 0.120 | 0.106 | 1.835 |
| MedGemma 1.5-4B | 0.075 | 0.134 | 0.078 | 0.072 | 1.294 |

## Runtime per model

| Model | Samples | Duration | Samples/hour |
|---|---|---|---|
| Gemini-3.1-Flash-Lite | 126 | 0:08:56 | 846.3 |
| Gemini 3.1 Pro | 126 | 1:23:46 | 90.3 |
| GPT-4o (v1 baseline model) | 126 | 0:02:43 | 2782.8 |
| GPT-5.4-mini | 126 | 0:07:02 | 1074.9 |
| GPT-5.5 | 126 | 0:41:04 | 184.1 |
| MedGemma 1.0-27B | 126 | 2:39:36 | 47.4 |
| MedGemma 1.5-4B | 126 | 5:08:46 | 24.5 |

## Statistical treatment

### Paired contrasts (condition-level, n=7)

| Contrast | Median difference (F1) | Wilcoxon W | p (two-tailed) | Favours A / Favours B / Ties |
|---|---|---|---|---|
| RAG vs non-RAG | +0.274 | 0.0 | 0.0156 | 7 / 0 / 0 |
| GPT-5.5 vs Gemini 3.1 Pro | +0.086 | 0.0 | 0.0156 | 7 / 0 / 0 |
| GPT-4o vs GPT-5.5 | -0.134 | 0.0 | 0.0156 | 0 / 7 / 0 |

No inference is reported on any model pair beyond these three, given the number of possible pairwise comparisons at seven models and the limited power available at seven conditions. Epochs within a combination are not pooled as independent observations, since they are repeated calls to the same model under the same settings. The seven clinical conditions were chosen to span a range of reference codelist sizes, not sampled from a larger population of conditions, so these tests describe this set and are not claimed to generalise beyond it. This analysis plan was written after the experiments had already run.

### Variance decomposition

Share of the total sum of squares in F1, across every individual epoch score in the dataset, attributable to each factor's own group means. The design is fully balanced (equal observations per level of every factor), so each factor's main-effect sum of squares is well-defined on its own; interaction effects are not separated out and fall into the residual.

| Factor | Share of total variance in F1 |
|---|---|
| Retrieval condition | 35.3% |
| Clinical condition | 15.6% |
| Model | 12.3% |
| Prompting strategy | 0.1% |
| Residual (interactions and noise) | 36.7% |

## Per-condition performance: mean across all combinations vs. best combination

"Mean" averages every model x strategy x retrieval_type combination tested on that condition, each already an average of its own 3 epochs. "Best" is the single highest-mean combination, named — not the highest individual epoch.

| Condition | Mean P | Mean R | Mean F1 | Best P | Best R | Best F1 | Best combination |
|---|---|---|---|---|---|---|---|
| Polymyalgia Rheumatica | 0.397 | 0.499 | 0.401 | 1.000 | 1.000 | 1.000 | GPT-5.5, chain_of_thought, rag |
| Multiple Sclerosis | 0.286 | 0.398 | 0.311 | 0.925 | 0.924 | 0.924 | GPT-5.5, few_shot, rag |
| Atrial Fibrillation | 0.221 | 0.369 | 0.249 | 0.468 | 0.750 | 0.575 | Gemini-3.1-Flash-Lite, few_shot, rag |
| Asthma | 0.276 | 0.238 | 0.216 | 0.533 | 0.667 | 0.592 | Gemini 3.1 Pro, few_shot, rag |
| Hypothyroidism | 0.251 | 0.210 | 0.209 | 0.563 | 0.606 | 0.583 | GPT-5.5, few_shot, rag |
| Type 2 Diabetes Mellitus | 0.092 | 0.312 | 0.123 | 0.264 | 0.478 | 0.339 | GPT-5.5, zero_shot, non_rag |
| Coronary Heart Disease | 0.241 | 0.042 | 0.069 | 0.638 | 0.113 | 0.191 | GPT-5.5, chain_of_thought, non_rag |

## F0.5 against F1

| Model | F1 | Rank (F1) | F0.5 | Rank (F0.5) | Gap (F0.5 − F1) |
|---|---|---|---|---|---|
| GPT-5.5 | 0.369 | 1 | 0.396 | 1 | +0.0267 |
| Gemini 3.1 Pro | 0.277 | 2 | 0.270 | 2 | -0.0069 |
| GPT-5.4-mini | 0.257 | 3 | 0.246 | 3 | -0.0107 |
| Gemini-3.1-Flash-Lite | 0.257 | 4 | 0.241 | 4 | -0.0151 |
| GPT-4o (v1 baseline model) | 0.220 | 5 | 0.238 | 5 | +0.0180 |
| MedGemma 1.0-27B | 0.120 | 6 | 0.106 | 6 | -0.0139 |
| MedGemma 1.5-4B | 0.078 | 7 | 0.072 | 7 | -0.0053 |

Rank correlation between F1 and F0.5: 1.000. Reorders any position: False.

## Fabricated identifiers

Proportion of generated codes (true and false positives together) identifying a real SNOMED-CT concept, by retrieval condition, plus the false-positive-only rate (excluding true positives, which are real by definition).

| Model | Non-retrieval | Retrieval-augmented | Overall | False-positive-only |
|---|---|---|---|---|
| Gemini-3.1-Flash-Lite | 25.2% | 99.9% | 81.8% | 75.0% |
| Gemini 3.1 Pro | 36.9% | 100.0% | 86.8% | 79.1% |
| GPT-4o (v1 baseline model) | 44.5% | 90.0% | 77.2% | 67.3% |
| GPT-5.4-mini | 49.1% | 99.2% | 88.9% | 85.4% |
| GPT-5.5 | 92.5% | 99.9% | 98.5% | 97.6% |
| MedGemma 1.0-27B | 9.1% | 88.1% | 63.9% | 59.0% |
| MedGemma 1.5-4B | 8.7% | 86.1% | 63.9% | 58.4% |

## Retrieval window size and repeat-call variance

Both analyses below required live model calls and are not recomputed by this script. They are embedded from the standalone runs already on disk.

### Retrieval window size test (GPT-4o, type 2 diabetes register standard, zero-shot, RAG)

| N | Precision | Recall | F1 | Fabricated identifiers (mean) |
|---|---|---|---|---|
| 50 | 0.149 ± 0.011 | 0.304 ± 0.000 | 0.200 ± 0.010 | 0.0 |
| 100 | 0.125 ± 0.007 | 0.478 ± 0.000 | 0.198 ± 0.008 | 0.0 |
| 200 | 0.171 ± 0.036 | 0.319 ± 0.050 | 0.219 ± 0.029 | 5.7 |
| 400 | 0.194 ± 0.028 | 0.362 ± 0.109 | 0.247 ± 0.025 | 3.0 |
| 500 | 0.164 ± 0.021 | 0.435 ± 0.075 | 0.236 ± 0.018 | 11.7 |
| 1000 | 0.120 ± 0.026 | 0.333 ± 0.025 | 0.175 ± 0.026 | 13.7 |

### Repeat-call variance (same prompt, 3 calls, one path at a time)

| Model | Path | Pairwise overlaps (% of the smaller response) |
|---|---|---|
| gpt-5.4-mini | chatlas | 27.3%, 26.5%, 25.0% |
| gpt-5.4-mini | native | 18.4%, 27.3%, 36.4% |
| gpt-5.5 | chatlas | 51.7%, 37.9%, 45.2% |
| gpt-5.5 | native | 46.9%, 55.9%, 68.8% |

## Sensitivity analyses

### Type 2 diabetes: audit standard substituted for register

Does substituting the 139-code audit standard for the 23-code register standard, in the seven-condition overall mean, change the model ranking?

| Model | Overall mean (register) | Overall mean (audit substituted) |
|---|---|---|
| Gemini-3.1-Flash-Lite | 0.257 | 0.290 |
| Gemini 3.1 Pro | 0.277 | 0.307 |
| GPT-4o (v1 baseline model) | 0.220 | 0.213 |
| GPT-5.4-mini | 0.257 | 0.283 |
| GPT-5.5 | 0.369 | 0.399 |
| MedGemma 1.0-27B | 0.120 | 0.126 |
| MedGemma 1.5-4B | 0.078 | 0.079 |

Ranking unchanged under substitution: False.

### Failed epochs dropped instead of scored zero

| Model | Failed / total epochs | Overall mean (scored zero) | Overall mean (dropped) |
|---|---|---|---|
| Gemini 3.1 Pro | 7/126 | 0.277 | 0.293 |
| MedGemma 1.0-27B | 2/126 | 0.120 | 0.122 |
| MedGemma 1.5-4B | 15/126 | 0.078 | 0.088 |

### Term-level scoring

A generated code counts as correct if its term matches a gold-standard term, whichever identifier carries it, pooled across all models. Reported for the three conditions with duplicate-term structure in their gold standard, plus atrial fibrillation as a control (no duplicate terms in that gold standard, so any gain there is not attributable to gold-standard duplication).

| Condition | Code-level recall | Term-level recall | Delta |
|---|---|---|---|
| Polymyalgia Rheumatica | 0.503 | 0.777 | 0.2740 |
| Multiple Sclerosis | 0.402 | 0.538 | 0.1367 |
| Asthma | 0.244 | 0.287 | 0.0432 |
| Atrial Fibrillation | 0.378 | 0.496 | 0.1182 |

### Macro vs micro averaging

Macro: each condition's own F1 averaged (the overall mean used throughout this report). Micro: true positives, false positives, and false negatives pooled across all seven conditions before computing precision, recall, and F1 once.

| Model | Macro F1 (overall mean) | Micro F1 |
|---|---|---|
| Gemini-3.1-Flash-Lite | 0.257 | 0.232 |
| Gemini 3.1 Pro | 0.277 | 0.271 |
| GPT-4o (v1 baseline model) | 0.220 | 0.147 |
| GPT-5.4-mini | 0.257 | 0.221 |
| GPT-5.5 | 0.369 | 0.313 |
| MedGemma 1.0-27B | 0.120 | 0.096 |
| MedGemma 1.5-4B | 0.078 | 0.074 |

Model order, macro: GPT-5.5 > Gemini 3.1 Pro > GPT-5.4-mini > Gemini-3.1-Flash-Lite > GPT-4o (v1 baseline model) > MedGemma 1.0-27B > MedGemma 1.5-4B

Model order, micro: GPT-5.5 > Gemini 3.1 Pro > Gemini-3.1-Flash-Lite > GPT-5.4-mini > GPT-4o (v1 baseline model) > MedGemma 1.0-27B > MedGemma 1.5-4B

## Coronary heart disease retrieval check

Anatomical-category codes present in the live corpus: 155/155.

| Category | Reference codes | Single search (N=400) | Multi-query, size-matched (16 x N=25) | Multi-query, unmatched (16 x N=400) |
|---|---|---|---|---|
| Anatomical | 155 | 0.0% | 19.4% | 84.5% |
| Complication | 29 | 0.0% | 31.0% | 93.1% |
| History | 11 | 0.0% | 63.6% | 90.9% |
| Procedure/admin | 3 | 0.0% | 66.7% | 100.0% |
| Diagnosis | 43 | 37.2% | 37.2% | 81.4% |
| Subtype | 93 | 11.8% | 28.0% | 76.3% |
| Whole condition | 336 | 8.0% | 26.8% | 82.4% |

## Model: Gemini-3.1-Flash-Lite

### Best RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | zero_shot | 0.494 | 0.648 | 0.560 | 0.518 | 1.312 |
| Atrial Fibrillation | few_shot | 0.468 | 0.750 | 0.575 | 0.506 | 1.611 |
| Coronary Heart Disease | few_shot | 0.307 | 0.073 | 0.119 | 0.188 | 0.239 |
| Hypothyroidism | few_shot | 0.560 | 0.560 | 0.560 | 0.560 | 1.000 |
| Multiple Sclerosis | few_shot | 0.833 | 0.909 | 0.870 | 0.847 | 1.091 |
| Polymyalgia Rheumatica | few_shot | 0.800 | 1.000 | 0.889 | 0.833 | 1.250 |
| Type 2 Diabetes Mellitus | few_shot | 0.100 | 0.870 | 0.179 | 0.121 | 8.725 |

### Best non-RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | zero_shot | 0.073 | 0.026 | 0.038 | 0.053 | 0.345 |
| Atrial Fibrillation | chain_of_thought | 0.059 | 0.083 | 0.069 | 0.063 | 1.417 |
| Coronary Heart Disease | chain_of_thought | 0.249 | 0.024 | 0.043 | 0.086 | 0.096 |
| Hypothyroidism | chain_of_thought | 0.041 | 0.010 | 0.016 | 0.026 | 0.244 |
| Multiple Sclerosis | few_shot | 0.032 | 0.023 | 0.026 | 0.029 | 0.720 |
| Polymyalgia Rheumatica | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 3.375 |
| Type 2 Diabetes Mellitus | chain_of_thought | 0.054 | 0.072 | 0.062 | 0.057 | 1.348 |

### Subtype (category) recall — at each condition's best RAG strategy

**Asthma** (strategy: zero_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.500 | 2.0 | 1.0 | 1.0 |
| S | 0.793 | 50.0 | 39.7 | 10.3 |
| V | 0.570 | 90.0 | 51.3 | 38.7 |

**Atrial Fibrillation** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.667 | 3.0 | 2.0 | 1.0 |
| S | 0.737 | 19.0 | 14.0 | 5.0 |
| V | 1.000 | 2.0 | 2.0 | 0.0 |

**Coronary Heart Disease** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| A | 0.000 | 155.0 | 0.0 | 155.0 |
| C | 0.000 | 29.0 | 0.0 | 29.0 |
| D | 0.364 | 43.0 | 15.7 | 27.3 |
| H | 0.000 | 11.0 | 0.0 | 11.0 |
| P | 0.000 | 3.0 | 0.0 | 3.0 |
| S | 0.097 | 93.0 | 9.0 | 84.0 |
| V | 0.000 | 2.0 | 0.0 | 2.0 |

**Hypothyroidism** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.333 | 3.0 | 1.0 | 2.0 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 0.558 | 126.0 | 70.3 | 55.7 |
| V | 1.000 | 1.0 | 1.0 | 0.0 |

**Multiple Sclerosis** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.889 | 9.0 | 8.0 | 1.0 |
| D | 1.000 | 4.0 | 4.0 | 0.0 |
| P | 0.000 | 1.0 | 0.0 | 1.0 |
| S | 0.913 | 23.0 | 21.0 | 2.0 |
| V | 1.000 | 7.0 | 7.0 | 0.0 |

**Polymyalgia Rheumatica** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 1.000 | 4.0 | 4.0 | 0.0 |
| H | 1.000 | 2.0 | 2.0 | 0.0 |
| S | 1.000 | 2.0 | 2.0 | 0.0 |

**Type 2 Diabetes Mellitus** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.867 | 15.0 | 13.0 | 2.0 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 1.000 | 4.0 | 4.0 | 0.0 |
| V | 0.667 | 3.0 | 2.0 | 1.0 |

### T2DM dual gold-standard sensitivity (main vs. audit) — best RAG strategy each

| Gold standard | Strategy | Precision | Recall | F1 | F0.5 | Size ratio | Gold count |
|---|---|---|---|---|---|---|---|
| Main (23 codes) | few_shot | 0.100 | 0.870 | 0.179 | 0.121 | 8.725 | 23 |
| Audit (139 codes) | few_shot | 0.578 | 0.834 | 0.683 | 0.616 | 1.444 | 139 |

### Flags

**Size ratio > 5.0** (generating far more codes than gold standard size):

- Type 2 Diabetes Mellitus / chain_of_thought / rag: size_ratio = 9.087
- Type 2 Diabetes Mellitus / few_shot / rag: size_ratio = 8.725
- Type 2 Diabetes Mellitus / zero_shot / rag: size_ratio = 9.623

**Recall = 0 across every RAG strategy for a category:**

- Coronary Heart Disease / category A
- Coronary Heart Disease / category C
- Coronary Heart Disease / category H
- Coronary Heart Disease / category P
- Coronary Heart Disease / category V

**Std > 0.15 on precision/recall/F1 (unstable across epochs):**

- Polymyalgia Rheumatica / chain_of_thought / rag: precision_std=0.263, f1_std=0.204

## Model: Gemini 3.1 Pro

### Best RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | few_shot | 0.533 | 0.667 | 0.592 | 0.555 | 1.251 |
| Atrial Fibrillation | few_shot | 0.423 | 0.792 | 0.551 | 0.466 | 1.875 |
| Coronary Heart Disease | zero_shot | 0.342 | 0.082 | 0.133 | 0.210 | 0.241 |
| Hypothyroidism | zero_shot | 0.560 | 0.595 | 0.577 | 0.567 | 1.066 |
| Multiple Sclerosis | zero_shot | 0.498 | 0.932 | 0.644 | 0.547 | 1.932 |
| Polymyalgia Rheumatica | chain_of_thought | 0.963 | 1.000 | 0.980 | 0.970 | 1.042 |
| Type 2 Diabetes Mellitus | zero_shot | 0.033 | 0.290 | 0.059 | 0.040 | 2.928 |

### Best non-RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | chain_of_thought | 0.212 | 0.045 | 0.073 | 0.121 | 0.216 |
| Atrial Fibrillation | chain_of_thought | 0.194 | 0.167 | 0.178 | 0.187 | 0.889 |
| Coronary Heart Disease | few_shot | 0.471 | 0.041 | 0.075 | 0.151 | 0.086 |
| Hypothyroidism | few_shot | 0.058 | 0.010 | 0.017 | 0.030 | 0.183 |
| Multiple Sclerosis | few_shot | 0.061 | 0.023 | 0.033 | 0.046 | 0.371 |
| Polymyalgia Rheumatica | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 1.083 |
| Type 2 Diabetes Mellitus | zero_shot | 0.166 | 0.290 | 0.211 | 0.181 | 1.725 |

### Subtype (category) recall — at each condition's best RAG strategy

**Asthma** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.333 | 2.0 | 0.7 | 1.3 |
| S | 0.840 | 50.0 | 42.0 | 8.0 |
| V | 0.578 | 90.0 | 52.0 | 38.0 |

**Atrial Fibrillation** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.667 | 3.0 | 2.0 | 1.0 |
| S | 0.789 | 19.0 | 15.0 | 4.0 |
| V | 1.000 | 2.0 | 2.0 | 0.0 |

**Coronary Heart Disease** (strategy: zero_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| A | 0.000 | 155.0 | 0.0 | 155.0 |
| C | 0.000 | 29.0 | 0.0 | 29.0 |
| D | 0.380 | 43.0 | 16.3 | 26.7 |
| H | 0.030 | 11.0 | 0.3 | 10.7 |
| P | 0.000 | 3.0 | 0.0 | 3.0 |
| S | 0.118 | 93.0 | 11.0 | 82.0 |
| V | 0.000 | 2.0 | 0.0 | 2.0 |

**Hypothyroidism** (strategy: zero_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.222 | 3.0 | 0.7 | 2.3 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 0.598 | 126.0 | 75.3 | 50.7 |
| V | 1.000 | 1.0 | 1.0 | 0.0 |

**Multiple Sclerosis** (strategy: zero_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.889 | 9.0 | 8.0 | 1.0 |
| D | 1.000 | 4.0 | 4.0 | 0.0 |
| P | 0.667 | 1.0 | 0.7 | 0.3 |
| S | 0.927 | 23.0 | 21.3 | 1.7 |
| V | 1.000 | 7.0 | 7.0 | 0.0 |

**Polymyalgia Rheumatica** (strategy: chain_of_thought)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 1.000 | 4.0 | 4.0 | 0.0 |
| H | 1.000 | 2.0 | 2.0 | 0.0 |
| S | 1.000 | 2.0 | 2.0 | 0.0 |

**Type 2 Diabetes Mellitus** (strategy: zero_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.867 | 15.0 | 13.0 | 2.0 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 1.000 | 4.0 | 4.0 | 0.0 |
| V | 0.667 | 3.0 | 2.0 | 1.0 |

### T2DM dual gold-standard sensitivity (main vs. audit) — best RAG strategy each

| Gold standard | Strategy | Precision | Recall | F1 | F0.5 | Size ratio | Gold count |
|---|---|---|---|---|---|---|---|
| Main (23 codes) | zero_shot | 0.033 | 0.290 | 0.059 | 0.040 | 2.928 | 23 |
| Audit (139 codes) | zero_shot | 0.579 | 0.842 | 0.686 | 0.618 | 1.453 | 139 |

### Flags

**Recall = 0 across every RAG strategy for a category:**

- Coronary Heart Disease / category A
- Coronary Heart Disease / category C
- Coronary Heart Disease / category P
- Coronary Heart Disease / category V

**Std > 0.15 on precision/recall/F1 (unstable across epochs):**

- Atrial Fibrillation / zero_shot / rag: precision_std=0.151, f1_std=0.161
- Type 2 Diabetes Mellitus / few_shot / rag: recall_std=0.502
- Type 2 Diabetes Mellitus / zero_shot / rag: recall_std=0.502

**Outright generation failures** (unparseable output after retries — 7/126 epochs overall, 5.6%):

- Type 2 Diabetes Mellitus / chain_of_thought / rag: 3/3 epochs failed
- Type 2 Diabetes Mellitus / few_shot / rag: 2/3 epochs failed
- Type 2 Diabetes Mellitus / zero_shot / rag: 2/3 epochs failed

## Model: GPT-4o (v1 baseline model)

### Best RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | zero_shot | 0.295 | 0.352 | 0.277 | 0.280 | 1.329 |
| Atrial Fibrillation | few_shot | 0.397 | 0.500 | 0.438 | 0.412 | 1.306 |
| Coronary Heart Disease | chain_of_thought | 0.241 | 0.026 | 0.047 | 0.090 | 0.108 |
| Hypothyroidism | zero_shot | 0.464 | 0.247 | 0.322 | 0.394 | 0.529 |
| Multiple Sclerosis | chain_of_thought | 0.660 | 0.629 | 0.640 | 0.651 | 0.947 |
| Polymyalgia Rheumatica | few_shot | 0.889 | 1.000 | 0.941 | 0.909 | 1.125 |
| Type 2 Diabetes Mellitus | chain_of_thought | 0.207 | 0.348 | 0.257 | 0.225 | 1.681 |

### Best non-RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | chain_of_thought | 0.381 | 0.061 | 0.105 | 0.185 | 0.157 |
| Atrial Fibrillation | zero_shot | 0.237 | 0.139 | 0.170 | 0.202 | 0.639 |
| Coronary Heart Disease | zero_shot | 0.286 | 0.020 | 0.037 | 0.077 | 0.069 |
| Hypothyroidism | chain_of_thought | 0.062 | 0.008 | 0.014 | 0.025 | 0.130 |
| Multiple Sclerosis | few_shot | 0.069 | 0.023 | 0.034 | 0.048 | 0.348 |
| Polymyalgia Rheumatica | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 1.208 |
| Type 2 Diabetes Mellitus | chain_of_thought | 0.129 | 0.116 | 0.122 | 0.126 | 0.928 |

### Subtype (category) recall — at each condition's best RAG strategy

**Asthma** (strategy: zero_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.500 | 2.0 | 1.0 | 1.0 |
| S | 0.533 | 50.0 | 26.7 | 23.3 |
| V | 0.248 | 90.0 | 22.3 | 67.7 |

**Atrial Fibrillation** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.667 | 3.0 | 2.0 | 1.0 |
| S | 0.456 | 19.0 | 8.7 | 10.3 |
| V | 0.667 | 2.0 | 1.3 | 0.7 |

**Coronary Heart Disease** (strategy: chain_of_thought)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| A | 0.000 | 155.0 | 0.0 | 155.0 |
| C | 0.000 | 29.0 | 0.0 | 29.0 |
| D | 0.140 | 43.0 | 6.0 | 37.0 |
| H | 0.030 | 11.0 | 0.3 | 10.7 |
| P | 0.000 | 3.0 | 0.0 | 3.0 |
| S | 0.025 | 93.0 | 2.3 | 90.7 |
| V | 0.000 | 2.0 | 0.0 | 2.0 |

**Hypothyroidism** (strategy: zero_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.000 | 3.0 | 0.0 | 3.0 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 0.241 | 126.0 | 30.3 | 95.7 |
| V | 1.000 | 1.0 | 1.0 | 0.0 |

**Multiple Sclerosis** (strategy: chain_of_thought)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.630 | 9.0 | 5.7 | 3.3 |
| D | 0.833 | 4.0 | 3.3 | 0.7 |
| P | 0.000 | 1.0 | 0.0 | 1.0 |
| S | 0.652 | 23.0 | 15.0 | 8.0 |
| V | 0.524 | 7.0 | 3.7 | 3.3 |

**Polymyalgia Rheumatica** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 1.000 | 4.0 | 4.0 | 0.0 |
| H | 1.000 | 2.0 | 2.0 | 0.0 |
| S | 1.000 | 2.0 | 2.0 | 0.0 |

**Type 2 Diabetes Mellitus** (strategy: chain_of_thought)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.333 | 15.0 | 5.0 | 10.0 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 0.250 | 4.0 | 1.0 | 3.0 |
| V | 0.333 | 3.0 | 1.0 | 2.0 |

### T2DM dual gold-standard sensitivity (main vs. audit) — best RAG strategy each

| Gold standard | Strategy | Precision | Recall | F1 | F0.5 | Size ratio | Gold count |
|---|---|---|---|---|---|---|---|
| Main (23 codes) | chain_of_thought | 0.207 | 0.348 | 0.257 | 0.225 | 1.681 | 23 |
| Audit (139 codes) | few_shot | 0.382 | 0.129 | 0.193 | 0.275 | 0.345 | 139 |

### Flags

**Recall = 0 across every RAG strategy for a category:**

- Coronary Heart Disease / category A
- Coronary Heart Disease / category C
- Coronary Heart Disease / category P
- Coronary Heart Disease / category V
- Hypothyroidism / category C

**Std > 0.15 on precision/recall/F1 (unstable across epochs):**

- Asthma / few_shot / non_rag: precision_std=0.177
- Asthma / zero_shot / rag: recall_std=0.282
- Multiple Sclerosis / chain_of_thought / rag: recall_std=0.151

## Model: GPT-5.4-mini

### Best RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | few_shot | 0.281 | 0.592 | 0.379 | 0.313 | 2.148 |
| Atrial Fibrillation | chain_of_thought | 0.355 | 0.764 | 0.473 | 0.394 | 2.472 |
| Coronary Heart Disease | few_shot | 0.201 | 0.068 | 0.100 | 0.142 | 0.389 |
| Hypothyroidism | chain_of_thought | 0.479 | 0.557 | 0.510 | 0.489 | 1.209 |
| Multiple Sclerosis | few_shot | 0.542 | 0.909 | 0.678 | 0.589 | 1.689 |
| Polymyalgia Rheumatica | chain_of_thought | 0.963 | 1.000 | 0.980 | 0.970 | 1.042 |
| Type 2 Diabetes Mellitus | chain_of_thought | 0.090 | 0.739 | 0.160 | 0.109 | 8.290 |

### Best non-RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | chain_of_thought | 0.359 | 0.075 | 0.124 | 0.204 | 0.214 |
| Atrial Fibrillation | zero_shot | 0.309 | 0.181 | 0.212 | 0.254 | 0.917 |
| Coronary Heart Disease | zero_shot | 0.342 | 0.047 | 0.082 | 0.150 | 0.139 |
| Hypothyroidism | chain_of_thought | 0.203 | 0.031 | 0.050 | 0.083 | 0.216 |
| Multiple Sclerosis | zero_shot | 0.083 | 0.038 | 0.042 | 0.052 | 0.795 |
| Polymyalgia Rheumatica | few_shot | 0.067 | 0.083 | 0.071 | 0.068 | 1.042 |
| Type 2 Diabetes Mellitus | few_shot | 0.232 | 0.145 | 0.167 | 0.196 | 0.899 |

### Subtype (category) recall — at each condition's best RAG strategy

**Asthma** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.333 | 2.0 | 0.7 | 1.3 |
| S | 0.693 | 50.0 | 34.7 | 15.3 |
| V | 0.541 | 90.0 | 48.7 | 41.3 |

**Atrial Fibrillation** (strategy: chain_of_thought)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.667 | 3.0 | 2.0 | 1.0 |
| S | 0.754 | 19.0 | 14.3 | 4.7 |
| V | 1.000 | 2.0 | 2.0 | 0.0 |

**Coronary Heart Disease** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| A | 0.000 | 155.0 | 0.0 | 155.0 |
| C | 0.000 | 29.0 | 0.0 | 29.0 |
| D | 0.318 | 43.0 | 13.7 | 29.3 |
| H | 0.000 | 11.0 | 0.0 | 11.0 |
| P | 0.000 | 3.0 | 0.0 | 3.0 |
| S | 0.100 | 93.0 | 9.3 | 83.7 |
| V | 0.000 | 2.0 | 0.0 | 2.0 |

**Hypothyroidism** (strategy: chain_of_thought)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.333 | 3.0 | 1.0 | 2.0 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 0.556 | 126.0 | 70.0 | 56.0 |
| V | 1.000 | 1.0 | 1.0 | 0.0 |

**Multiple Sclerosis** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.852 | 9.0 | 7.7 | 1.3 |
| D | 1.000 | 4.0 | 4.0 | 0.0 |
| P | 0.000 | 1.0 | 0.0 | 1.0 |
| S | 0.928 | 23.0 | 21.3 | 1.7 |
| V | 1.000 | 7.0 | 7.0 | 0.0 |

**Polymyalgia Rheumatica** (strategy: chain_of_thought)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 1.000 | 4.0 | 4.0 | 0.0 |
| H | 1.000 | 2.0 | 2.0 | 0.0 |
| S | 1.000 | 2.0 | 2.0 | 0.0 |

**Type 2 Diabetes Mellitus** (strategy: chain_of_thought)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.733 | 15.0 | 11.0 | 4.0 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 0.750 | 4.0 | 3.0 | 1.0 |
| V | 0.667 | 3.0 | 2.0 | 1.0 |

### T2DM dual gold-standard sensitivity (main vs. audit) — best RAG strategy each

| Gold standard | Strategy | Precision | Recall | F1 | F0.5 | Size ratio | Gold count |
|---|---|---|---|---|---|---|---|
| Main (23 codes) | chain_of_thought | 0.090 | 0.739 | 0.160 | 0.109 | 8.290 | 23 |
| Audit (139 codes) | chain_of_thought | 0.508 | 0.693 | 0.585 | 0.536 | 1.372 | 139 |

### Flags

**Size ratio > 5.0** (generating far more codes than gold standard size):

- Type 2 Diabetes Mellitus / chain_of_thought / rag: size_ratio = 8.290
- Type 2 Diabetes Mellitus / few_shot / rag: size_ratio = 7.406
- Type 2 Diabetes Mellitus / zero_shot / rag: size_ratio = 6.130

**Recall = 0 across every RAG strategy for a category:**

- Coronary Heart Disease / category A
- Coronary Heart Disease / category C
- Coronary Heart Disease / category H
- Coronary Heart Disease / category P
- Coronary Heart Disease / category V
- Multiple Sclerosis / category P

**Std > 0.15 on precision/recall/F1 (unstable across epochs):**

- Atrial Fibrillation / zero_shot / non_rag: precision_std=0.217
- Atrial Fibrillation / zero_shot / rag: precision_std=0.221, f1_std=0.221
- Polymyalgia Rheumatica / zero_shot / rag: precision_std=0.421, f1_std=0.352
- Type 2 Diabetes Mellitus / few_shot / non_rag: precision_std=0.188
- Type 2 Diabetes Mellitus / zero_shot / rag: recall_std=0.196
- Type 2 Diabetes Mellitus (Audit) / few_shot / non_rag: precision_std=0.178
- Type 2 Diabetes Mellitus (Audit) / zero_shot / rag: recall_std=0.208

## Model: GPT-5.5

### Best RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | few_shot | 0.476 | 0.667 | 0.554 | 0.504 | 1.413 |
| Atrial Fibrillation | few_shot | 0.396 | 0.792 | 0.528 | 0.440 | 2.000 |
| Coronary Heart Disease | few_shot | 0.388 | 0.103 | 0.163 | 0.250 | 0.266 |
| Hypothyroidism | few_shot | 0.563 | 0.606 | 0.583 | 0.571 | 1.076 |
| Multiple Sclerosis | few_shot | 0.925 | 0.924 | 0.924 | 0.925 | 1.000 |
| Polymyalgia Rheumatica | chain_of_thought | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| Type 2 Diabetes Mellitus | chain_of_thought | 0.096 | 0.855 | 0.172 | 0.116 | 8.942 |

### Best non-RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | few_shot | 0.682 | 0.176 | 0.280 | 0.433 | 0.258 |
| Atrial Fibrillation | few_shot | 0.618 | 0.319 | 0.421 | 0.520 | 0.514 |
| Coronary Heart Disease | chain_of_thought | 0.638 | 0.113 | 0.191 | 0.328 | 0.182 |
| Hypothyroidism | chain_of_thought | 0.513 | 0.107 | 0.177 | 0.291 | 0.209 |
| Multiple Sclerosis | zero_shot | 0.553 | 0.151 | 0.237 | 0.360 | 0.273 |
| Polymyalgia Rheumatica | few_shot | 0.833 | 0.167 | 0.274 | 0.451 | 0.208 |
| Type 2 Diabetes Mellitus | zero_shot | 0.264 | 0.478 | 0.339 | 0.289 | 1.884 |

### Subtype (category) recall — at each condition's best RAG strategy

**Asthma** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.500 | 2.0 | 1.0 | 1.0 |
| S | 0.820 | 50.0 | 41.0 | 9.0 |
| V | 0.585 | 90.0 | 52.7 | 37.3 |

**Atrial Fibrillation** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.667 | 3.0 | 2.0 | 1.0 |
| S | 0.789 | 19.0 | 15.0 | 4.0 |
| V | 1.000 | 2.0 | 2.0 | 0.0 |

**Coronary Heart Disease** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| A | 0.000 | 155.0 | 0.0 | 155.0 |
| C | 0.000 | 29.0 | 0.0 | 29.0 |
| D | 0.411 | 43.0 | 17.7 | 25.3 |
| H | 0.061 | 11.0 | 0.7 | 10.3 |
| P | 0.000 | 3.0 | 0.0 | 3.0 |
| S | 0.176 | 93.0 | 16.3 | 76.7 |
| V | 0.000 | 2.0 | 0.0 | 2.0 |

**Hypothyroidism** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.333 | 3.0 | 1.0 | 2.0 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 0.606 | 126.0 | 76.3 | 49.7 |
| V | 1.000 | 1.0 | 1.0 | 0.0 |

**Multiple Sclerosis** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.889 | 9.0 | 8.0 | 1.0 |
| D | 1.000 | 4.0 | 4.0 | 0.0 |
| P | 0.000 | 1.0 | 0.0 | 1.0 |
| S | 0.942 | 23.0 | 21.7 | 1.3 |
| V | 1.000 | 7.0 | 7.0 | 0.0 |

**Polymyalgia Rheumatica** (strategy: chain_of_thought)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 1.000 | 4.0 | 4.0 | 0.0 |
| H | 1.000 | 2.0 | 2.0 | 0.0 |
| S | 1.000 | 2.0 | 2.0 | 0.0 |

**Type 2 Diabetes Mellitus** (strategy: chain_of_thought)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.844 | 15.0 | 12.7 | 2.3 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 1.000 | 4.0 | 4.0 | 0.0 |
| V | 0.667 | 3.0 | 2.0 | 1.0 |

### T2DM dual gold-standard sensitivity (main vs. audit) — best RAG strategy each

| Gold standard | Strategy | Precision | Recall | F1 | F0.5 | Size ratio | Gold count |
|---|---|---|---|---|---|---|---|
| Main (23 codes) | chain_of_thought | 0.096 | 0.855 | 0.172 | 0.116 | 8.942 | 23 |
| Audit (139 codes) | zero_shot | 0.562 | 0.834 | 0.672 | 0.601 | 1.484 | 139 |

### Flags

**Size ratio > 5.0** (generating far more codes than gold standard size):

- Type 2 Diabetes Mellitus / chain_of_thought / rag: size_ratio = 8.942
- Type 2 Diabetes Mellitus / few_shot / rag: size_ratio = 8.855
- Type 2 Diabetes Mellitus / zero_shot / rag: size_ratio = 8.971

**Recall = 0 across every RAG strategy for a category:**

- Coronary Heart Disease / category A
- Coronary Heart Disease / category C
- Coronary Heart Disease / category P
- Coronary Heart Disease / category V

**Std > 0.15 on precision/recall/F1 (unstable across epochs):**

- Atrial Fibrillation / chain_of_thought / non_rag: precision_std=0.210
- Multiple Sclerosis / chain_of_thought / non_rag: precision_std=0.339
- Polymyalgia Rheumatica / chain_of_thought / non_rag: precision_std=0.151
- Polymyalgia Rheumatica / few_shot / non_rag: precision_std=0.289
- Polymyalgia Rheumatica / zero_shot / non_rag: precision_std=0.462

## Model: MedGemma 1.0-27B

### Best RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | zero_shot | 0.286 | 0.207 | 0.240 | 0.266 | 0.721 |
| Atrial Fibrillation | few_shot | 0.179 | 0.486 | 0.259 | 0.204 | 2.806 |
| Coronary Heart Disease | chain_of_thought | 0.060 | 0.023 | 0.033 | 0.045 | 0.391 |
| Hypothyroidism | few_shot | 0.251 | 0.206 | 0.225 | 0.240 | 0.845 |
| Multiple Sclerosis | chain_of_thought | 0.390 | 0.477 | 0.429 | 0.404 | 1.220 |
| Polymyalgia Rheumatica | chain_of_thought | 0.658 | 1.000 | 0.781 | 0.701 | 1.625 |
| Type 2 Diabetes Mellitus | zero_shot | 0.112 | 0.377 | 0.172 | 0.130 | 3.464 |

### Best non-RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | chain_of_thought | 0.011 | 0.002 | 0.004 | 0.006 | 0.249 |
| Atrial Fibrillation | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 1.236 |
| Coronary Heart Disease | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 0.096 |
| Hypothyroidism | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 0.239 |
| Multiple Sclerosis | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 0.606 |
| Polymyalgia Rheumatica | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 2.875 |
| Type 2 Diabetes Mellitus | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 1.435 |

### Subtype (category) recall — at each condition's best RAG strategy

**Asthma** (strategy: zero_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.500 | 2.0 | 1.0 | 1.0 |
| S | 0.380 | 50.0 | 19.0 | 31.0 |
| V | 0.104 | 90.0 | 9.3 | 80.7 |

**Atrial Fibrillation** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.889 | 3.0 | 2.7 | 0.3 |
| S | 0.368 | 19.0 | 7.0 | 12.0 |
| V | 1.000 | 2.0 | 2.0 | 0.0 |

**Coronary Heart Disease** (strategy: chain_of_thought)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| A | 0.000 | 155.0 | 0.0 | 155.0 |
| C | 0.000 | 29.0 | 0.0 | 29.0 |
| D | 0.101 | 43.0 | 4.3 | 38.7 |
| H | 0.000 | 11.0 | 0.0 | 11.0 |
| P | 0.000 | 3.0 | 0.0 | 3.0 |
| S | 0.036 | 93.0 | 3.3 | 89.7 |
| V | 0.000 | 2.0 | 0.0 | 2.0 |

**Hypothyroidism** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.000 | 3.0 | 0.0 | 3.0 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 0.198 | 126.0 | 25.0 | 101.0 |
| V | 1.000 | 1.0 | 1.0 | 0.0 |

**Multiple Sclerosis** (strategy: chain_of_thought)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.296 | 9.0 | 2.7 | 6.3 |
| D | 0.667 | 4.0 | 2.7 | 1.3 |
| P | 0.000 | 1.0 | 0.0 | 1.0 |
| S | 0.594 | 23.0 | 13.7 | 9.3 |
| V | 0.286 | 7.0 | 2.0 | 5.0 |

**Polymyalgia Rheumatica** (strategy: chain_of_thought)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 1.000 | 4.0 | 4.0 | 0.0 |
| H | 1.000 | 2.0 | 2.0 | 0.0 |
| S | 1.000 | 2.0 | 2.0 | 0.0 |

**Type 2 Diabetes Mellitus** (strategy: zero_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.244 | 15.0 | 3.7 | 11.3 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 0.500 | 4.0 | 2.0 | 2.0 |
| V | 0.667 | 3.0 | 2.0 | 1.0 |

### T2DM dual gold-standard sensitivity (main vs. audit) — best RAG strategy each

| Gold standard | Strategy | Precision | Recall | F1 | F0.5 | Size ratio | Gold count |
|---|---|---|---|---|---|---|---|
| Main (23 codes) | zero_shot | 0.112 | 0.377 | 0.172 | 0.130 | 3.464 | 23 |
| Audit (139 codes) | chain_of_thought | 0.307 | 0.285 | 0.296 | 0.302 | 0.930 | 139 |

### Flags

**Size ratio > 5.0** (generating far more codes than gold standard size):

- Polymyalgia Rheumatica / few_shot / non_rag: size_ratio = 5.042
- Polymyalgia Rheumatica / few_shot / rag: size_ratio = 6.917
- Polymyalgia Rheumatica / zero_shot / rag: size_ratio = 6.250
- Type 2 Diabetes Mellitus / chain_of_thought / rag: size_ratio = 5.623

**Recall = 0 across every RAG strategy for a category:**

- Coronary Heart Disease / category A
- Coronary Heart Disease / category C
- Coronary Heart Disease / category H
- Coronary Heart Disease / category P
- Coronary Heart Disease / category V

**Std > 0.15 on precision/recall/F1 (unstable across epochs):**

- Asthma / few_shot / rag: precision_std=0.157
- Multiple Sclerosis / few_shot / rag: recall_std=0.172
- Polymyalgia Rheumatica / chain_of_thought / rag: precision_std=0.212, f1_std=0.152
- Polymyalgia Rheumatica / few_shot / rag: f1_std=0.167
- Polymyalgia Rheumatica / zero_shot / rag: precision_std=0.171, f1_std=0.223

**Outright generation failures** (unparseable output after retries — 2/126 epochs overall, 1.6%):

- Asthma / chain_of_thought / rag: 1/3 epochs failed
- Asthma / few_shot / rag: 1/3 epochs failed

## Model: MedGemma 1.5-4B

### Best RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | zero_shot | 0.308 | 0.157 | 0.207 | 0.256 | 0.516 |
| Atrial Fibrillation | zero_shot | 0.127 | 0.292 | 0.173 | 0.142 | 1.625 |
| Coronary Heart Disease | few_shot | 0.080 | 0.016 | 0.026 | 0.041 | 0.183 |
| Hypothyroidism | zero_shot | 0.176 | 0.132 | 0.151 | 0.165 | 0.504 |
| Multiple Sclerosis | zero_shot | 0.355 | 0.417 | 0.376 | 0.362 | 1.182 |
| Polymyalgia Rheumatica | few_shot | 0.294 | 0.833 | 0.419 | 0.333 | 3.417 |
| Type 2 Diabetes Mellitus | few_shot | 0.082 | 0.232 | 0.121 | 0.094 | 2.797 |

### Best non-RAG strategy per condition

| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |
|---|---|---|---|---|---|---|
| Asthma | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 0.153 |
| Atrial Fibrillation | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 0.903 |
| Coronary Heart Disease | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 0.050 |
| Hypothyroidism | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 0.120 |
| Multiple Sclerosis | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 0.561 |
| Polymyalgia Rheumatica | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 1.250 |
| Type 2 Diabetes Mellitus | chain_of_thought | 0.000 | 0.000 | 0.000 | 0.000 | 1.000 |

### Subtype (category) recall — at each condition's best RAG strategy

**Asthma** (strategy: zero_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.333 | 2.0 | 0.7 | 1.3 |
| S | 0.333 | 50.0 | 16.7 | 33.3 |
| V | 0.056 | 90.0 | 5.0 | 85.0 |

**Atrial Fibrillation** (strategy: zero_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 1.000 | 3.0 | 3.0 | 0.0 |
| S | 0.289 | 19.0 | 5.5 | 13.5 |
| V | 1.000 | 2.0 | 2.0 | 0.0 |

**Coronary Heart Disease** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| A | 0.000 | 155.0 | 0.0 | 155.0 |
| C | 0.000 | 29.0 | 0.0 | 29.0 |
| D | 0.078 | 43.0 | 3.3 | 39.7 |
| H | 0.000 | 11.0 | 0.0 | 11.0 |
| P | 0.000 | 3.0 | 0.0 | 3.0 |
| S | 0.022 | 93.0 | 2.0 | 91.0 |
| V | 0.000 | 2.0 | 0.0 | 2.0 |

**Hypothyroidism** (strategy: zero_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.000 | 3.0 | 0.0 | 3.0 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 0.190 | 126.0 | 24.0 | 102.0 |
| V | 1.000 | 1.0 | 1.0 | 0.0 |

**Multiple Sclerosis** (strategy: zero_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.074 | 9.0 | 0.7 | 8.3 |
| D | 1.000 | 4.0 | 4.0 | 0.0 |
| P | 0.000 | 1.0 | 0.0 | 1.0 |
| S | 0.377 | 23.0 | 8.7 | 14.3 |
| V | 0.714 | 7.0 | 5.0 | 2.0 |

**Polymyalgia Rheumatica** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| D | 0.667 | 4.0 | 2.7 | 1.3 |
| H | 1.000 | 2.0 | 2.0 | 0.0 |
| S | 1.000 | 2.0 | 2.0 | 0.0 |

**Type 2 Diabetes Mellitus** (strategy: few_shot)

| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |
|---|---|---|---|---|
| C | 0.067 | 15.0 | 1.0 | 14.0 |
| D | 1.000 | 1.0 | 1.0 | 0.0 |
| S | 0.500 | 4.0 | 2.0 | 2.0 |
| V | 0.444 | 3.0 | 1.3 | 1.7 |

### T2DM dual gold-standard sensitivity (main vs. audit) — best RAG strategy each

| Gold standard | Strategy | Precision | Recall | F1 | F0.5 | Size ratio | Gold count |
|---|---|---|---|---|---|---|---|
| Main (23 codes) | few_shot | 0.082 | 0.232 | 0.121 | 0.094 | 2.797 | 23 |
| Audit (139 codes) | chain_of_thought | 0.227 | 0.130 | 0.163 | 0.195 | 0.583 | 139 |

### Flags

**Size ratio > 5.0** (generating far more codes than gold standard size):

- Polymyalgia Rheumatica / zero_shot / rag: size_ratio = 15.792

**Recall = 0 across every RAG strategy for a category:**

- Coronary Heart Disease / category A
- Coronary Heart Disease / category C
- Coronary Heart Disease / category H
- Coronary Heart Disease / category P
- Coronary Heart Disease / category V
- Multiple Sclerosis / category P

**Std > 0.15 on precision/recall/F1 (unstable across epochs):**

- Atrial Fibrillation / chain_of_thought / rag: recall_std=0.253
- Atrial Fibrillation / few_shot / rag: recall_std=0.206
- Atrial Fibrillation / zero_shot / rag: recall_std=0.260, f1_std=0.151
- Hypothyroidism / chain_of_thought / rag: precision_std=0.164
- Hypothyroidism / zero_shot / rag: precision_std=0.153
- Multiple Sclerosis / chain_of_thought / rag: recall_std=0.193, f1_std=0.165
- Multiple Sclerosis / few_shot / rag: precision_std=0.160, recall_std=0.290, f1_std=0.206
- Polymyalgia Rheumatica / chain_of_thought / rag: recall_std=0.545, f1_std=0.176
- Polymyalgia Rheumatica / few_shot / rag: precision_std=0.179, f1_std=0.191
- Type 2 Diabetes Mellitus / chain_of_thought / rag: recall_std=0.230
- Type 2 Diabetes Mellitus / zero_shot / rag: recall_std=0.176

**Outright generation failures** (unparseable output after retries — 15/126 epochs overall, 11.9%):

- Asthma / chain_of_thought / rag: 1/3 epochs failed
- Atrial Fibrillation / chain_of_thought / rag: 1/3 epochs failed
- Atrial Fibrillation / few_shot / rag: 1/3 epochs failed
- Atrial Fibrillation / zero_shot / rag: 1/3 epochs failed
- Coronary Heart Disease / chain_of_thought / rag: 1/3 epochs failed
- Coronary Heart Disease / zero_shot / rag: 1/3 epochs failed
- Hypothyroidism / chain_of_thought / non_rag: 1/3 epochs failed
- Hypothyroidism / chain_of_thought / rag: 1/3 epochs failed
- Hypothyroidism / few_shot / rag: 2/3 epochs failed
- Hypothyroidism / zero_shot / rag: 1/3 epochs failed
- Multiple Sclerosis / few_shot / rag: 1/3 epochs failed
- Polymyalgia Rheumatica / chain_of_thought / rag: 1/3 epochs failed
- Type 2 Diabetes Mellitus / chain_of_thought / rag: 1/3 epochs failed
- Type 2 Diabetes Mellitus / zero_shot / rag: 1/3 epochs failed
