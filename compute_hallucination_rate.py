"""Standalone script: real-code rate per model, both overall (TP+FP) and
restricted to false positives only.

Overall rate mixes in true positives, which are always real by construction
(a TP only occurs when the generated code matches a gold-standard code).
That dilutes the fake-code signal, especially for high-recall models. The
false-positive-only rate isolates the actually interesting question: of the
codes each model got wrong, what fraction were invented outright versus
real-but-mismatched concepts.

Reads every inspect_results/*/*_code_breakdown_metrics.csv, no re-scoring.
"""

import glob

import pandas as pd

FILES = sorted(glob.glob("inspect_results/*/*_code_breakdown_metrics.csv"))

rows = []
for path in FILES:
    df = pd.read_csv(path)
    for model_label, g in df.groupby("model_label"):
        combined = g[g["eval_category"].isin(["true_positive", "false_positive"])]
        fp_only = g[g["eval_category"] == "false_positive"]
        rows.append(
            {
                "model_label": model_label,
                "n_true_positive": (g["eval_category"] == "true_positive").sum(),
                "n_false_positive": len(fp_only),
                "overall_real_rate": combined["code_is_real"].mean(),
                "fp_only_real_rate": fp_only["code_is_real"].mean() if len(fp_only) else float("nan"),
            }
        )

out = pd.DataFrame(rows).sort_values("fp_only_real_rate", ascending=False)
out["overall_fake_rate_pct"] = ((1 - out["overall_real_rate"]) * 100).round(1)
out["fp_only_fake_rate_pct"] = ((1 - out["fp_only_real_rate"]) * 100).round(1)

print(out[["model_label", "n_true_positive", "n_false_positive",
           "overall_fake_rate_pct", "fp_only_fake_rate_pct"]].to_string(index=False))

out.to_csv("outputs/hallucination_rate_by_model.csv", index=False)
print("\nSaved to outputs/hallucination_rate_by_model.csv")
