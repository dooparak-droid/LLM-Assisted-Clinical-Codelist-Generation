"""Standalone script: validity check for the CHD zero-recall finding.

Distinguishes "code was never retrieved" (retrieval_failure) from "code was
retrieved but not selected by the model" (generation_failure), per gold
category, using each model's existing RAG-only retrieval_attribution.csv
(already computed by inspect_pipeline.py's evaluate_retrieval_attribution())
joined against the categorised CHD gold standard for category labels.

No re-scoring or re-retrieval needed - the attribution data already exists
per sample; this just aggregates it by category.
"""

import glob

import pandas as pd

GOLD = (
    pd.read_csv("data/categorised_gold_standards/chd_cod_categorised.csv")
    .rename(columns={"category": "gold_category"})[["code", "gold_category"]]
)

rows = []
for path in sorted(glob.glob("inspect_results/*/*_retrieval_attribution.csv")):
    ra = pd.read_csv(path)
    if "code" not in ra.columns or ra.empty:
        continue
    chd = ra[ra["condition"] == "Coronary Heart Disease"]
    if chd.empty:
        continue
    model_label = chd["model_label"].iloc[0]
    chd = chd.merge(GOLD, on="code", how="left")
    ct = pd.crosstab(chd["gold_category"], chd["failure_type"])
    for cat, r in ct.iterrows():
        retrieval_failure = int(r.get("retrieval_failure", 0))
        generation_failure = int(r.get("generation_failure", 0))
        total = retrieval_failure + generation_failure
        rows.append(
            {
                "model_label": model_label,
                "gold_category": cat,
                "n_retrieval_failure": retrieval_failure,
                "n_generation_failure": generation_failure,
                "pct_retrieval_failure": round(100 * retrieval_failure / total, 1) if total else float("nan"),
            }
        )

out = pd.DataFrame(rows).sort_values(["gold_category", "model_label"])
print(out.to_string(index=False))
out.to_csv("outputs/chd_retrieval_diagnosis.csv", index=False)
print("\nSaved to outputs/chd_retrieval_diagnosis.csv")
