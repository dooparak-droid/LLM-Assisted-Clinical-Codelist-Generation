"""Standalone script: manual-audit support for the code_is_real metric.

Samples 30 codes flagged as fabricated (code_is_real == False, false_positive
rows only) across all models, then checks each against the FULL RF2 Concept
snapshot (International + UK Clinical, active AND inactive) - a broader
reference than the active-only ChromaDB corpus that code_is_real was
originally checked against. This directly tests whether "fabricated" codes
are genuinely nonexistent, or are real-but-inactive/excluded concepts that
the corpus-completeness check in the analysis brief was worried about.

Requires the RF2 files already present under data/snomed/ (see
notebooks/02_snomed_preprocessing.ipynb for the same paths used to build the
ChromaDB corpus).
"""

import glob

import pandas as pd

INTL_CONCEPT = (
    "data/snomed/SnomedCT_InternationalRF2_PRODUCTION_20260201T120000Z/"
    "Snapshot/Terminology/sct2_Concept_Snapshot_INT_20260201.txt"
)
UKCL_CONCEPT = (
    "data/snomed/SnomedCT_UKClinicalRF2_PRODUCTION_20260506T000001Z/"
    "Snapshot/Terminology/sct2_Concept_UKCLSnapshot_GB1000000_20260506.txt"
)

concepts = pd.concat(
    [
        pd.read_csv(INTL_CONCEPT, sep="\t", dtype={"id": str}, usecols=["id", "active"]),
        pd.read_csv(UKCL_CONCEPT, sep="\t", dtype={"id": str}, usecols=["id", "active"]),
    ],
    ignore_index=True,
)
concepts = concepts.drop_duplicates(subset="id")
concept_active = dict(zip(concepts["id"], concepts["active"]))

frames = []
for path in glob.glob("inspect_results/*/*_code_breakdown_metrics.csv"):
    df = pd.read_csv(path)
    fp = df[(df["eval_category"] == "false_positive") & (~df["code_is_real"])]
    frames.append(fp[["model_label", "condition", "code", "term"]])

all_fabricated = pd.concat(frames, ignore_index=True)
sample = all_fabricated.sample(n=30, random_state=42).copy()
sample["code_str"] = sample["code"].astype(str)
sample["found_in_full_rf2"] = sample["code_str"].isin(concept_active.keys())
sample["rf2_active_status"] = sample["code_str"].map(
    lambda c: {1: "active", 0: "inactive"}.get(concept_active.get(c), "not_found")
)

print(sample[["model_label", "condition", "code", "term", "found_in_full_rf2", "rf2_active_status"]].to_string(index=False))
print()
print("Summary:")
print(sample["rf2_active_status"].value_counts())

sample.to_csv("outputs/audit_sample_fabricated_codes.csv", index=False)
print("\nSaved to outputs/audit_sample_fabricated_codes.csv")
