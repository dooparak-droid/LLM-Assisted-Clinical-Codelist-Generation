# generate_analysis_report.py

"""
Standalone report generator: reads every model's pooled_metrics.csv,
subtype_metrics_pooled.csv, per_epoch_metrics.csv, and code_breakdown_metrics.csv
already sitting in inspect_results/*/ (written by derive_csvs() in
inspect_pipeline.py) and produces a single markdown summary at
outputs/analysis_report.md — no re-scoring, no log reading, just a fast
read-and-summarize pass over CSVs that already exist.

Run after any derive_csvs() call (or derive_csvs_only.py) to refresh the
report against whatever models currently have results on disk:

    python3 generate_analysis_report.py
    python3 generate_analysis_report.py --with-retrieval-checks

Design notes (decisions made when this was scoped with the user):
  - "Best RAG strategy" and "best non-RAG strategy" are reported side by
    side per condition, rather than a single best-overall pick, since
    RAG vs. non-RAG is itself one of the dissertation's research questions
    (RQ4) — collapsing that comparison away would hide the thing being
    studied.
  - The subtype/category recall table is anchored to each condition's
    already-identified best RAG strategy (not a full strategy x category
    cross product) so it reads as "here's what's weak in the strategy
    you'd actually use," not a wall of redundant numbers.
  - T2DM's audit gold-standard row (added via inspect_pipeline.py's dual
    gold-standard sensitivity pass) is reported in its own subsection,
    never folded into the main 7-condition tables, so it can't be
    mistaken for an eighth "real" condition.
  - If a model's folder has more than one file matching *pooled_metrics.csv
    (a stale prefix left over from a naming change, say), the most
    recently modified one wins — same convention as derive_csvs_only.py's
    find_latest_log().

2026-08-16 additions (folded in from the Results-chapter drafting session,
so this script stays the single source of truth rather than the analysis
living only in one-off scratch scripts):
  - Statistical treatment: three designated paired contrasts (Wilcoxon
    signed-rank, condition-level, n=7) and one variance decomposition.
  - Sensitivity analyses: T2DM audit-standard substitution, failed-epochs
    dropped vs. scored zero, term-level scoring, macro vs. micro averaging.
  - Fabricated-identifier rate split by retrieval condition, plus the
    false-positive-only rate.
  - F0.5 against F1: does F0.5 reorder anything, and by how much.
  - A combined per-condition table (mean across all combinations vs. the
    single best combination, named).
  - Two analyses needed live model calls and were run once as standalone
    scripts (writing/run_n_sweep.py, writing/run_path_baseline.py) — this
    report embeds their saved output rather than re-running them.
  - The coronary heart disease retrieval check (corpus presence + hand-
    written multi-query test, size-matched and unmatched) needs the full
    retrieval stack (embedding model, ChromaDB, BM25), which is slow to
    load relative to the rest of this script — gated behind
    --with-retrieval-checks so a normal run stays fast.
"""

import argparse
import glob
import json
import os

import pandas as pd
from scipy.stats import spearmanr, wilcoxon

RESULTS_DIR = "inspect_results"
OUTPUT_PATH = "outputs/analysis_report.md"
N_SWEEP_PATH = "writing/n_sweep_gpt4o_t2dm_summary.csv"
PATH_BASELINE_PATH = "writing/path_baseline_results.json"
CHD_GOLD_PATH = "data/categorised_gold_standards/chd_cod_categorised.csv"

TERM_LEVEL_GOLD_FILES = {
    "Polymyalgia Rheumatica": "data/categorised_gold_standards/pmr_cod_categorised.csv",
    "Multiple Sclerosis": "data/categorised_gold_standards/ms_cod_categorised.csv",
    "Asthma": "data/categorised_gold_standards/ast_cod_categorised.csv",
    "Atrial Fibrillation": "data/categorised_gold_standards/afib_cod_categorised.csv",
}

CHD_MULTI_QUERY_SEARCH_TERMS = {
    "D": ["myocardial infarction", "coronary artery disease", "acute coronary syndrome"],
    "S": ["postoperative myocardial infarction", "coronary arteriosclerosis", "myocardial ischemia during surgery"],
    "C": ["complication of myocardial infarction", "cardiac rupture after myocardial infarction", "pericardial effusion after heart attack"],
    "A": ["infarction of papillary muscle", "occlusion of coronary artery branch", "ST elevation myocardial infarction site"],
    "H": ["history of myocardial infarction", "history of coronary artery bypass graft"],
    "P": ["coronary artery bypass graft", "coronary angioplasty"],
}

SIZE_RATIO_FLAG_THRESHOLD = 5.0
STD_FLAG_THRESHOLD = 0.15
GENERATION_FAILURE_FLAG_THRESHOLD = 1  # flag a combo with >= this many outright-failed epochs


def _latest(paths):
    return max(paths, key=os.path.getmtime)


def find_model_folders(results_dir):
    """
    Returns {model_dir_name: (pooled_df, subtype_pooled_df, per_epoch_df,
    run_metadata_df, code_breakdown_df)} for every subdirectory of
    results_dir that has a *pooled_metrics.csv, a *subtype_metrics_pooled.csv,
    and a *per_epoch_metrics.csv (skips *_metrics_pooled or plain
    pooled_metrics matches ambiguously — see _latest() above for the
    stale-duplicate tie-break). per_epoch_df feeds the generation-failure-
    rate flag (see build_flags_section) — n_attempts/error_message aren't
    in any CSV (only the .eval log), but a fully failed sample always has
    generated_count == 0, which is. run_metadata_df (runtime/n_samples) and
    code_breakdown_df (fabrication rate, term-level/micro-averaging
    sensitivity checks) are both optional — an empty DataFrame if a
    model's folder predates that file, so older results still render with
    those sections skipped rather than the whole run failing.
    """
    models = {}
    for entry in sorted(os.listdir(results_dir)):
        model_dir = os.path.join(results_dir, entry)
        if not os.path.isdir(model_dir):
            continue

        pooled_candidates = [
            p
            for p in glob.glob(os.path.join(model_dir, "*pooled_metrics.csv"))
            if not p.endswith("subtype_metrics_pooled.csv")
        ]
        subtype_candidates = glob.glob(
            os.path.join(model_dir, "*subtype_metrics_pooled.csv")
        )
        per_epoch_candidates = glob.glob(
            os.path.join(model_dir, "*per_epoch_metrics.csv")
        )
        run_metadata_candidates = glob.glob(
            os.path.join(model_dir, "*run_metadata.csv")
        )
        code_breakdown_candidates = glob.glob(
            os.path.join(model_dir, "*code_breakdown_metrics.csv")
        )
        if not pooled_candidates or not subtype_candidates or not per_epoch_candidates:
            continue

        pooled_df = pd.read_csv(_latest(pooled_candidates))
        subtype_df = pd.read_csv(_latest(subtype_candidates))
        per_epoch_df = pd.read_csv(_latest(per_epoch_candidates))
        run_metadata_df = (
            pd.read_csv(_latest(run_metadata_candidates))
            if run_metadata_candidates
            else pd.DataFrame()
        )
        code_breakdown_df = (
            pd.read_csv(_latest(code_breakdown_candidates))
            if code_breakdown_candidates
            else pd.DataFrame()
        )
        models[entry] = (pooled_df, subtype_df, per_epoch_df, run_metadata_df, code_breakdown_df)
    return models


def _fmt(x, decimals=3):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n/a"
    return f"{x:.{decimals}f}"


def best_strategy_table(pooled_df, condition, retrieval_type):
    """
    Returns the single row (as a dict) with the highest f1_mean among rows
    for this condition + retrieval_type, or None if there are no such rows.
    """
    subset = pooled_df[
        (pooled_df["condition"] == condition) & (pooled_df["retrieval_type"] == retrieval_type)
    ]
    if subset.empty:
        return None
    return subset.loc[subset["f1_mean"].idxmax()].to_dict()


def build_best_strategy_section(pooled_df, conditions, retrieval_type, title):
    lines = [f"### {title}", ""]
    lines.append(
        "| Condition | Strategy | Precision | Recall | F1 | F0.5 | Size ratio |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for condition in conditions:
        row = best_strategy_table(pooled_df, condition, retrieval_type)
        if row is None:
            lines.append(f"| {condition} | *(no {retrieval_type} data)* | | | | | |")
            continue
        lines.append(
            f"| {condition} | {row['strategy']} "
            f"| {_fmt(row['precision_mean'])} | {_fmt(row['recall_mean'])} "
            f"| {_fmt(row['f1_mean'])} | {_fmt(row['f05_mean'])} "
            f"| {_fmt(row['size_ratio_mean'])} |"
        )
    lines.append("")
    return lines


def build_subtype_section(pooled_df, subtype_df, conditions):
    """
    For each condition, anchors to the best RAG strategy already identified
    and shows that strategy's recall broken down by SNOMED category.
    Conditions with no RAG rows at all are skipped (nothing to anchor to).
    """
    lines = ["### Subtype (category) recall — at each condition's best RAG strategy", ""]
    for condition in conditions:
        best_row = best_strategy_table(pooled_df, condition, "rag")
        if best_row is None:
            continue
        strategy = best_row["strategy"]
        cat_rows = subtype_df[
            (subtype_df["condition"] == condition)
            & (subtype_df["strategy"] == strategy)
            & (subtype_df["retrieval_type"] == "rag")
        ].sort_values("category")
        if cat_rows.empty:
            continue
        lines.append(f"**{condition}** (strategy: {strategy})")
        lines.append("")
        lines.append("| Category | Recall | Gold count (mean) | TP (mean) | FN (mean) |")
        lines.append("|---|---|---|---|---|")
        for _, r in cat_rows.iterrows():
            lines.append(
                f"| {r['category']} | {_fmt(r['recall_mean'])} "
                f"| {_fmt(r['gold_count_mean'], 1)} | {_fmt(r['tp_count_mean'], 1)} "
                f"| {_fmt(r['fn_count_mean'], 1)} |"
            )
        lines.append("")
    return lines


def build_audit_section(pooled_df):
    """
    T2DM main vs. audit gold-standard comparison, kept entirely separate
    from the main per-condition tables (see module docstring).
    """
    main_row = best_strategy_table(pooled_df, "Type 2 Diabetes Mellitus", "rag")
    audit_row = best_strategy_table(pooled_df, "Type 2 Diabetes Mellitus (Audit)", "rag")
    if main_row is None and audit_row is None:
        return []

    lines = [
        "### T2DM dual gold-standard sensitivity (main vs. audit) — best RAG strategy each",
        "",
        "| Gold standard | Strategy | Precision | Recall | F1 | F0.5 | Size ratio | Gold count |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for label, row in [("Main (23 codes)", main_row), ("Audit (139 codes)", audit_row)]:
        if row is None:
            lines.append(f"| {label} | *(no data)* | | | | | | |")
            continue
        lines.append(
            f"| {label} | {row['strategy']} | {_fmt(row['precision_mean'])} "
            f"| {_fmt(row['recall_mean'])} | {_fmt(row['f1_mean'])} "
            f"| {_fmt(row['f05_mean'])} | {_fmt(row['size_ratio_mean'])} "
            f"| {_fmt(row['gold_count_mean'], 0)} |"
        )
    lines.append("")
    return lines


def build_flags_section(pooled_df, subtype_df, per_epoch_df, conditions):
    """
    Flags:
      - size_ratio_mean > SIZE_RATIO_FLAG_THRESHOLD on any pooled row
      - a condition/category with recall_mean == 0 across every RAG
        strategy (i.e. RAG never retrieves/generates that category at all)
      - any of precision_std/recall_std/f1_std > STD_FLAG_THRESHOLD
        (unstable across epochs)
      - outright generation failures: a sample where the model's output
        couldn't be parsed into any codes at all (generated_count == 0 —
        n_attempts/error_message aren't in any CSV, only the .eval log, but
        a fully-failed sample always has generated_count == 0 after
        exhausting MAX_RETRIES). These are already scored as 0 precision/
        recall/F1 in the pooled averages above (not excluded), so this flag
        exists to surface *how many* of those zeros were genuine parse
        failures rather than the model validly producing an empty list.
    """
    lines = ["### Flags", ""]
    found_any = False

    size_flags = pooled_df[pooled_df["size_ratio_mean"] > SIZE_RATIO_FLAG_THRESHOLD]
    if not size_flags.empty:
        found_any = True
        lines.append(f"**Size ratio > {SIZE_RATIO_FLAG_THRESHOLD}** (generating far more codes than gold standard size):")
        lines.append("")
        for _, r in size_flags.iterrows():
            lines.append(
                f"- {r['condition']} / {r['strategy']} / {r['retrieval_type']}: "
                f"size_ratio = {_fmt(r['size_ratio_mean'])}"
            )
        lines.append("")

    rag_subtype = subtype_df[subtype_df["retrieval_type"] == "rag"]
    zero_recall_flags = []
    for condition in conditions:
        cond_subtype = rag_subtype[rag_subtype["condition"] == condition]
        for category in sorted(cond_subtype["category"].unique()):
            cat_rows = cond_subtype[cond_subtype["category"] == category]
            if not cat_rows.empty and (cat_rows["recall_mean"] == 0).all():
                zero_recall_flags.append((condition, category))
    if zero_recall_flags:
        found_any = True
        lines.append("**Recall = 0 across every RAG strategy for a category:**")
        lines.append("")
        for condition, category in zero_recall_flags:
            lines.append(f"- {condition} / category {category}")
        lines.append("")

    std_cols = ["precision_std", "recall_std", "f1_std"]
    std_flags = pooled_df[(pooled_df[std_cols] > STD_FLAG_THRESHOLD).any(axis=1)]
    if not std_flags.empty:
        found_any = True
        lines.append(f"**Std > {STD_FLAG_THRESHOLD} on precision/recall/F1 (unstable across epochs):**")
        lines.append("")
        for _, r in std_flags.iterrows():
            unstable = [
                f"{col.replace('_std', '')}_std={_fmt(r[col])}"
                for col in std_cols
                if r[col] > STD_FLAG_THRESHOLD
            ]
            lines.append(
                f"- {r['condition']} / {r['strategy']} / {r['retrieval_type']}: "
                + ", ".join(unstable)
            )
        lines.append("")

    failure_source = per_epoch_df.copy()
    failure_source["failed"] = failure_source["generated_count"] == 0
    failure_group_cols = ["condition", "strategy", "retrieval_type"]
    failure_counts = failure_source.groupby(failure_group_cols).agg(
        n_epochs=("failed", "size"), n_failed=("failed", "sum")
    ).reset_index()
    failure_flags = failure_counts[failure_counts["n_failed"] >= GENERATION_FAILURE_FLAG_THRESHOLD]
    if not failure_flags.empty:
        found_any = True
        total_failed = int(failure_flags["n_failed"].sum())
        total_epochs = int(per_epoch_df.shape[0])
        lines.append(
            f"**Outright generation failures** (unparseable output after retries — "
            f"{total_failed}/{total_epochs} epochs overall, {total_failed / total_epochs:.1%}):"
        )
        lines.append("")
        for _, r in failure_flags.iterrows():
            lines.append(
                f"- {r['condition']} / {r['strategy']} / {r['retrieval_type']}: "
                f"{int(r['n_failed'])}/{int(r['n_epochs'])} epochs failed"
            )
        lines.append("")

    if not found_any:
        lines.append("No flags triggered.")
        lines.append("")

    return lines


def build_cross_model_table(models):
    """
    Two rows-per-model tables, not one: a "best RAG strategy" mean and an
    "overall" mean, side by side by design (not just the best one — see the
    explanatory note below). Best-strategy cherry-picks each condition's
    top strategy per model, which is an optimistic ceiling on what a
    practitioner would get by chance; the overall mean (every
    condition x strategy x retrieval_type cell, including non-RAG and
    weaker strategies) is the honest expectation over the full design.
    Reporting only the former overstates every model uniformly; reporting
    only the latter buries how much strategy choice matters. Both exclude
    the T2DM audit condition — it's a sensitivity check on one condition,
    not an eighth data point that should dilute the cross-model average.
    """
    lines = [
        "## Cross-model comparison",
        "",
        "Two means are reported per model, deliberately, not one:",
        "",
        "- **Best-strategy mean**: for each condition, the single best-performing "
        "RAG strategy, averaged across conditions. An optimistic ceiling — what "
        "a practitioner gets *if* they already knew which strategy to pick.",
        "- **Overall mean**: every condition x strategy x retrieval_type cell "
        "(including non-RAG and the weaker strategies), averaged. The honest "
        "expectation over the full experimental design, with no post-hoc "
        "strategy selection.",
        "",
        "The gap between the two is itself informative — a large gap means "
        "strategy/retrieval choice matters a lot for that model; a small gap "
        "means the model is robust to it.",
        "",
        "### Best RAG strategy mean",
        "",
        "| Model | Precision | Recall | F1 | F0.5 | Size ratio |",
        "|---|---|---|---|---|---|",
    ]
    best_rows = {}
    overall_rows = {}
    for model_dir, (pooled_df, _, _, _, _) in models.items():
        conditions = [
            c for c in pooled_df["condition"].unique() if "Audit" not in c
        ]
        rows = [best_strategy_table(pooled_df, c, "rag") for c in conditions]
        rows = [r for r in rows if r is not None]
        if not rows:
            continue
        model_label = rows[0]["model_label"]
        avg_df = pd.DataFrame(rows)
        best_rows[model_label] = avg_df
        lines.append(
            f"| {model_label} | {_fmt(avg_df['precision_mean'].mean())} "
            f"| {_fmt(avg_df['recall_mean'].mean())} | {_fmt(avg_df['f1_mean'].mean())} "
            f"| {_fmt(avg_df['f05_mean'].mean())} | {_fmt(avg_df['size_ratio_mean'].mean())} |"
        )

        overall_df = pooled_df[~pooled_df["condition"].isin(
            [c for c in pooled_df["condition"].unique() if "Audit" in c]
        )]
        overall_rows[model_label] = overall_df

    lines.append("")
    lines.append("### Overall mean (all conditions x strategies x retrieval types)")
    lines.append("")
    lines.append("| Model | Precision | Recall | F1 | F0.5 | Size ratio |")
    lines.append("|---|---|---|---|---|---|")
    for model_label, overall_df in overall_rows.items():
        lines.append(
            f"| {model_label} | {_fmt(overall_df['precision_mean'].mean())} "
            f"| {_fmt(overall_df['recall_mean'].mean())} | {_fmt(overall_df['f1_mean'].mean())} "
            f"| {_fmt(overall_df['f05_mean'].mean())} | {_fmt(overall_df['size_ratio_mean'].mean())} |"
        )
    lines.append("")
    return lines


def build_runtime_table(models):
    """
    One row per model with a run_metadata.csv (written by derive_csvs() from
    the .eval log's own started_at/completed_at timestamps — exact wall-clock
    duration, not a parsed terminal summary). Models whose results predate
    this file (run_metadata_df empty) are listed with "n/a" rather than
    silently dropped, so the table still names every model in the report.
    Also reports samples/hour as a rough throughput comparison — useful
    since local Ollama models and API models have very different cost
    profiles (time vs. $) that a raw duration alone doesn't convey.
    """
    lines = [
        "## Runtime per model",
        "",
        "| Model | Samples | Duration | Samples/hour |",
        "|---|---|---|---|",
    ]
    for model_dir, (pooled_df, _, _, run_metadata_df, _) in models.items():
        model_label = pooled_df["model_label"].iloc[0]
        if run_metadata_df.empty:
            lines.append(f"| {model_label} | n/a | n/a | n/a |")
            continue
        row = run_metadata_df.iloc[0]
        rate = row["n_samples"] / (row["duration_seconds"] / 3600) if row["duration_seconds"] > 0 else 0
        lines.append(
            f"| {model_label} | {int(row['n_samples'])} | {row['duration_hms']} | {rate:.1f} |"
        )
    lines.append("")
    return lines


def _model_label(pooled_df):
    return pooled_df["model_label"].iloc[0]


def _condition_level_f1_map(per_epoch_df, main_conditions):
    """Mean F1 per (main, non-audit) condition for one model's per_epoch_df."""
    df = per_epoch_df[per_epoch_df["condition"].isin(main_conditions)]
    return df.groupby("condition")["f1"].mean()


def build_statistical_treatment_section(models):
    """
    Three designated paired contrasts (condition-level, n=7) plus one
    variance decomposition. Added after the first draft of the Results
    chapter, since the earlier version of this report had no inferential
    support behind the three headline claims it already made descriptively
    (RAG vs. non-RAG, GPT-5.5 vs. Gemini 3.1 Pro, GPT-4o vs. GPT-5.5).

    At n=7 conditions the two-tailed Wilcoxon signed-rank floor is
    p=0.0156, reached only when every one of the seven pairs runs in the
    same direction — this is reported as "consistent across all seven
    conditions," not as strong evidence in the conventional sense.
    """
    all_pe = []
    for _, (_, _, per_epoch_df, _, _) in models.items():
        df = per_epoch_df[~per_epoch_df["condition"].str.contains("Audit", na=False)]
        all_pe.append(df)
    full = pd.concat(all_pe, ignore_index=True)
    conditions = sorted(full["condition"].unique())

    lines = ["## Statistical treatment", "", "### Paired contrasts (condition-level, n=7)", ""]
    lines.append("| Contrast | Median difference (F1) | Wilcoxon W | p (two-tailed) | Favours A / Favours B / Ties |")
    lines.append("|---|---|---|---|---|")

    def series_for(filter_fn):
        return full[filter_fn(full)].groupby("condition")["f1"].mean().reindex(conditions)

    labels_present = set(full["model_label"].unique())
    gpt4o_labels = [l for l in labels_present if "GPT-4o" in l]

    contrasts = []
    if {"rag", "non_rag"} <= set(full["retrieval_type"].unique()):
        contrasts.append((
            "RAG vs non-RAG",
            series_for(lambda d: d["retrieval_type"] == "rag"),
            series_for(lambda d: d["retrieval_type"] == "non_rag"),
        ))
    if {"GPT-5.5", "Gemini 3.1 Pro"} <= labels_present:
        contrasts.append((
            "GPT-5.5 vs Gemini 3.1 Pro",
            series_for(lambda d: d["model_label"] == "GPT-5.5"),
            series_for(lambda d: d["model_label"] == "Gemini 3.1 Pro"),
        ))
    if gpt4o_labels and "GPT-5.5" in labels_present:
        contrasts.append((
            "GPT-4o vs GPT-5.5",
            series_for(lambda d: d["model_label"] == gpt4o_labels[0]),
            series_for(lambda d: d["model_label"] == "GPT-5.5"),
        ))

    for name, a, b in contrasts:
        if a.isna().any() or b.isna().any():
            lines.append(f"| {name} | *(incomplete data across the seven conditions)* | | | |")
            continue
        diffs = a - b
        stat, p = wilcoxon(a, b)
        n_a = int((diffs > 0).sum())
        n_b = int((diffs < 0).sum())
        n_tie = int((diffs == 0).sum())
        lines.append(f"| {name} | {diffs.median():+.3f} | {stat:.1f} | {p:.4f} | {n_a} / {n_b} / {n_tie} |")
    lines.append("")
    lines.append(
        "No inference is reported on any model pair beyond these three, given the "
        "number of possible pairwise comparisons at seven models and the limited "
        "power available at seven conditions. Epochs within a combination are not "
        "pooled as independent observations, since they are repeated calls to the "
        "same model under the same settings. The seven clinical conditions were "
        "chosen to span a range of reference codelist sizes, not sampled from a "
        "larger population of conditions, so these tests describe this set and are "
        "not claimed to generalise beyond it. This analysis plan was written after "
        "the experiments had already run."
    )
    lines.append("")

    lines.append("### Variance decomposition")
    lines.append("")
    lines.append(
        "Share of the total sum of squares in F1, across every individual epoch "
        "score in the dataset, attributable to each factor's own group means. The "
        "design is fully balanced (equal observations per level of every factor), "
        "so each factor's main-effect sum of squares is well-defined on its own; "
        "interaction effects are not separated out and fall into the residual."
    )
    lines.append("")
    grand_mean = full["f1"].mean()
    ss_total = ((full["f1"] - grand_mean) ** 2).sum()
    factor_cols = {
        "Retrieval condition": "retrieval_type",
        "Clinical condition": "condition",
        "Model": "model_label",
        "Prompting strategy": "strategy",
    }
    lines.append("| Factor | Share of total variance in F1 |")
    lines.append("|---|---|")
    ss_main_total = 0.0
    for label, col in factor_cols.items():
        grp_means = full.groupby(col)["f1"].transform("mean")
        ss = ((grp_means - grand_mean) ** 2).sum()
        ss_main_total += ss
        lines.append(f"| {label} | {100 * ss / ss_total:.1f}% |")
    lines.append(f"| Residual (interactions and noise) | {100 * (ss_total - ss_main_total) / ss_total:.1f}% |")
    lines.append("")
    return lines


def build_sensitivity_section(models):
    """
    Four checks against stored output, no regeneration of any model call.
    """
    lines = ["## Sensitivity analyses", ""]

    # --- 1. T2DM audit standard substituted for register ---
    lines.append("### Type 2 diabetes: audit standard substituted for register")
    lines.append("")
    lines.append(
        "Does substituting the 139-code audit standard for the 23-code register "
        "standard, in the seven-condition overall mean, change the model ranking?"
    )
    lines.append("")
    lines.append("| Model | Overall mean (register) | Overall mean (audit substituted) |")
    lines.append("|---|---|---|")
    rank_rows = []
    for _, (pooled_df, _, _, _, _) in models.items():
        label = _model_label(pooled_df)
        conds_register = [c for c in pooled_df["condition"].unique() if "Audit" not in c]
        overall_r = pooled_df[pooled_df["condition"].isin(conds_register)]["f1_mean"].mean()
        conds_audit = [c for c in conds_register if c != "Type 2 Diabetes Mellitus"] + [
            "Type 2 Diabetes Mellitus (Audit)"
        ]
        present_audit = [c for c in conds_audit if c in pooled_df["condition"].unique()]
        overall_a = (
            pooled_df[pooled_df["condition"].isin(present_audit)]["f1_mean"].mean()
            if len(present_audit) == len(conds_audit)
            else float("nan")
        )
        lines.append(f"| {label} | {_fmt(overall_r)} | {_fmt(overall_a)} |")
        rank_rows.append((label, overall_r, overall_a))

    order_register = [x[0] for x in sorted(rank_rows, key=lambda t: -t[1])]
    complete_audit = [x for x in rank_rows if not pd.isna(x[2])]
    order_audit = [x[0] for x in sorted(complete_audit, key=lambda t: -t[2])]
    lines.append("")
    if len(complete_audit) == len(rank_rows):
        lines.append(f"Ranking unchanged under substitution: {order_register == order_audit}.")
    else:
        lines.append(
            f"Ranking comparison incomplete — {len(rank_rows) - len(complete_audit)} "
            f"model(s) have no audit-condition rows."
        )
    lines.append("")

    # --- 2. Failed epochs dropped instead of scored zero ---
    lines.append("### Failed epochs dropped instead of scored zero")
    lines.append("")
    lines.append("| Model | Failed / total epochs | Overall mean (scored zero) | Overall mean (dropped) |")
    lines.append("|---|---|---|---|")
    any_failures = False
    for _, (_, _, per_epoch_df, _, _) in models.items():
        pe = per_epoch_df[~per_epoch_df["condition"].str.contains("Audit", na=False)]
        label = pe["model_label"].iloc[0]
        failed = (pe["true_positives"] == 0) & (pe["false_positives"] == 0) & (pe["generated_count"] == 0)
        n_fail = int(failed.sum())
        if n_fail == 0:
            continue
        any_failures = True
        f1_zero = pe["f1"].mean()
        f1_dropped = pe[~failed]["f1"].mean()
        lines.append(f"| {label} | {n_fail}/{len(pe)} | {_fmt(f1_zero)} | {_fmt(f1_dropped)} |")
    if not any_failures:
        lines.append("| *(no model had any failed epochs)* | | | |")
    lines.append("")

    # --- 3. Term-level scoring ---
    lines.append("### Term-level scoring")
    lines.append("")
    lines.append(
        "A generated code counts as correct if its term matches a gold-standard "
        "term, whichever identifier carries it, pooled across all models. Reported "
        "for the three conditions with duplicate-term structure in their gold "
        "standard, plus atrial fibrillation as a control (no duplicate terms in "
        "that gold standard, so any gain there is not attributable to gold-standard "
        "duplication)."
    )
    lines.append("")
    all_bd = [
        code_breakdown_df
        for _, (_, _, _, _, code_breakdown_df) in models.items()
        if code_breakdown_df is not None and not code_breakdown_df.empty
    ]
    if all_bd:
        full_bd = pd.concat(all_bd, ignore_index=True)
        lines.append("| Condition | Code-level recall | Term-level recall | Delta |")
        lines.append("|---|---|---|---|")
        for cond in TERM_LEVEL_GOLD_FILES:
            sub = full_bd[full_bd["condition"] == cond]
            if sub.empty:
                continue
            tp = (sub["eval_category"] == "true_positive").sum()
            fn = (sub["eval_category"] == "false_negative").sum()
            code_recall = tp / (tp + fn) if (tp + fn) else float("nan")
            group_cols = ["strategy", "retrieval_type", "epoch", "model_label", "condition"]
            term_tp, term_total = 0, 0
            for _, g in sub.groupby(group_cols):
                gen_terms = set(
                    g[g["eval_category"].isin(["true_positive", "false_positive"])]["term"]
                    .astype(str).str.strip().str.lower()
                )
                gold_rows = g[g["eval_category"].isin(["true_positive", "false_negative"])]
                for _, row in gold_rows.iterrows():
                    term_total += 1
                    if str(row["term"]).strip().lower() in gen_terms:
                        term_tp += 1
            term_recall = term_tp / term_total if term_total else float("nan")
            delta = term_recall - code_recall if not (pd.isna(term_recall) or pd.isna(code_recall)) else float("nan")
            lines.append(f"| {cond} | {_fmt(code_recall)} | {_fmt(term_recall)} | {_fmt(delta, 4)} |")
        lines.append("")
    else:
        lines.append("*(no code_breakdown_metrics.csv files found across any model — skipped)*")
        lines.append("")

    # --- 4. Macro vs micro averaging ---
    lines.append("### Macro vs micro averaging")
    lines.append("")
    lines.append(
        "Macro: each condition's own F1 averaged (the overall mean used throughout "
        "this report). Micro: true positives, false positives, and false negatives "
        "pooled across all seven conditions before computing precision, recall, and "
        "F1 once."
    )
    lines.append("")
    lines.append("| Model | Macro F1 (overall mean) | Micro F1 |")
    lines.append("|---|---|---|")
    macro_rank, micro_rank = [], []
    for _, (pooled_df, _, _, _, code_breakdown_df) in models.items():
        label = _model_label(pooled_df)
        conds_register = [c for c in pooled_df["condition"].unique() if "Audit" not in c]
        macro_f1 = pooled_df[pooled_df["condition"].isin(conds_register)]["f1_mean"].mean()
        if code_breakdown_df is None or code_breakdown_df.empty:
            micro_f1 = float("nan")
        else:
            bd = code_breakdown_df[~code_breakdown_df["condition"].str.contains("Audit", na=False)]
            tp = (bd["eval_category"] == "true_positive").sum()
            fp = (bd["eval_category"] == "false_positive").sum()
            fn = (bd["eval_category"] == "false_negative").sum()
            p = tp / (tp + fp) if (tp + fp) else 0
            r = tp / (tp + fn) if (tp + fn) else 0
            micro_f1 = 2 * p * r / (p + r) if (p + r) else 0
        lines.append(f"| {label} | {_fmt(macro_f1)} | {_fmt(micro_f1)} |")
        macro_rank.append((label, macro_f1))
        if not pd.isna(micro_f1):
            micro_rank.append((label, micro_f1))
    macro_order = [x[0] for x in sorted(macro_rank, key=lambda t: -t[1])]
    micro_order = [x[0] for x in sorted(micro_rank, key=lambda t: -t[1])]
    lines.append("")
    lines.append(f"Model order, macro: {' > '.join(macro_order)}")
    lines.append("")
    lines.append(f"Model order, micro: {' > '.join(micro_order)}")
    lines.append("")
    return lines


def build_fabrication_section(models):
    """
    Requires code_is_real to already be present in a model's
    code_breakdown_metrics.csv (derive_csvs() computes this automatically
    against the live SNOMED-CT corpus). Models without it are skipped.
    """
    lines = ["## Fabricated identifiers", ""]
    lines.append(
        "Proportion of generated codes (true and false positives together) "
        "identifying a real SNOMED-CT concept, by retrieval condition, plus the "
        "false-positive-only rate (excluding true positives, which are real by "
        "definition)."
    )
    lines.append("")
    lines.append("| Model | Non-retrieval | Retrieval-augmented | Overall | False-positive-only |")
    lines.append("|---|---|---|---|---|")
    for _, (_, _, _, _, code_breakdown_df) in models.items():
        if (
            code_breakdown_df is None
            or code_breakdown_df.empty
            or "code_is_real" not in code_breakdown_df.columns
        ):
            continue
        bd = code_breakdown_df[~code_breakdown_df["condition"].str.contains("Audit", na=False)]
        label = _model_label(bd)
        gen = bd[bd["eval_category"].isin(["true_positive", "false_positive"])]
        if gen.empty:
            continue
        by_rt = gen.groupby("retrieval_type")["code_is_real"].mean()
        overall = gen["code_is_real"].mean()
        fp_only = bd[bd["eval_category"] == "false_positive"]
        fp_rate = fp_only["code_is_real"].mean() if not fp_only.empty else float("nan")
        non_rag_pct = 100 * by_rt.get("non_rag", float("nan"))
        rag_pct = 100 * by_rt.get("rag", float("nan"))
        lines.append(
            f"| {label} | {_fmt(non_rag_pct, 1)}% | {_fmt(rag_pct, 1)}% "
            f"| {100 * overall:.1f}% | {_fmt(100 * fp_rate, 1)}% |"
        )
    lines.append("")
    return lines


def build_f05_vs_f1_section(models):
    """
    Whether F0.5 (precision-weighted) reorders the cross-model ranking F1
    already gives, and how large the gap runs per model.
    """
    lines = ["## F0.5 against F1", ""]
    rows = []
    for _, (pooled_df, _, _, _, _) in models.items():
        conds = [c for c in pooled_df["condition"].unique() if "Audit" not in c]
        sub = pooled_df[pooled_df["condition"].isin(conds)]
        rows.append({
            "model": _model_label(pooled_df),
            "f1": sub["f1_mean"].mean(),
            "f05": sub["f05_mean"].mean(),
        })
    out = pd.DataFrame(rows)
    out["gap"] = out["f05"] - out["f1"]
    by_f1 = out.sort_values("f1", ascending=False).reset_index(drop=True)
    by_f1["rank_f1"] = by_f1.index + 1
    by_f05 = out.sort_values("f05", ascending=False).reset_index(drop=True)
    by_f05["rank_f05"] = by_f05.index + 1
    merged = by_f1.merge(by_f05[["model", "rank_f05"]], on="model")

    lines.append("| Model | F1 | Rank (F1) | F0.5 | Rank (F0.5) | Gap (F0.5 − F1) |")
    lines.append("|---|---|---|---|---|---|")
    for _, r in merged.iterrows():
        lines.append(
            f"| {r['model']} | {_fmt(r['f1'])} | {int(r['rank_f1'])} "
            f"| {_fmt(r['f05'])} | {int(r['rank_f05'])} | {r['gap']:+.4f} |"
        )
    lines.append("")
    if len(merged) >= 2:
        rho, _ = spearmanr(merged["rank_f1"], merged["rank_f05"])
        reordered = bool((merged["rank_f1"] != merged["rank_f05"]).any())
        lines.append(f"Rank correlation between F1 and F0.5: {rho:.3f}. Reorders any position: {reordered}.")
        lines.append("")
    return lines


def build_combined_per_condition_table(models):
    """
    "Best" here is the highest COMBINATION mean (a model x strategy x
    retrieval_type row, already averaged over its 3 epochs), never the
    highest individual epoch score — taking a maximum over raw epochs
    would select for favourable epoch noise rather than genuine
    performance. Not restricted to RAG: the single best combination for a
    condition can be, and for some conditions is, a non-retrieval one.
    """
    all_pooled = []
    for _, (pooled_df, _, _, _, _) in models.items():
        df = pooled_df[~pooled_df["condition"].str.contains("Audit", na=False)]
        all_pooled.append(df)
    full = pd.concat(all_pooled, ignore_index=True)

    lines = ["## Per-condition performance: mean across all combinations vs. best combination", ""]
    lines.append(
        "\"Mean\" averages every model x strategy x retrieval_type combination "
        "tested on that condition, each already an average of its own 3 epochs. "
        "\"Best\" is the single highest-mean combination, named — not the highest "
        "individual epoch."
    )
    lines.append("")
    lines.append("| Condition | Mean P | Mean R | Mean F1 | Best P | Best R | Best F1 | Best combination |")
    lines.append("|---|---|---|---|---|---|---|---|")
    row_data = []
    for cond in full["condition"].unique():
        sub = full[full["condition"] == cond]
        mean_p, mean_r, mean_f1 = (
            sub["precision_mean"].mean(),
            sub["recall_mean"].mean(),
            sub["f1_mean"].mean(),
        )
        best = sub.loc[sub["f1_mean"].idxmax()]
        row_data.append({
            "condition": cond,
            "mean_f1": mean_f1,
            "line": (
                f"| {cond} | {_fmt(mean_p)} | {_fmt(mean_r)} | {_fmt(mean_f1)} "
                f"| {_fmt(best['precision_mean'])} | {_fmt(best['recall_mean'])} | {_fmt(best['f1_mean'])} "
                f"| {best['model_label']}, {best['strategy']}, {best['retrieval_type']} |"
            ),
        })
    for r in sorted(row_data, key=lambda x: -x["mean_f1"]):
        lines.append(r["line"])
    lines.append("")
    return lines


def build_external_precomputed_section():
    """
    Two analyses needed live model calls and were run once as standalone
    scripts (writing/run_n_sweep.py, writing/run_path_baseline.py), not as
    part of this report's normal read-only pass over stored CSVs. This
    section embeds whatever those scripts already left on disk without
    re-running them — if a file isn't there, the section says so and moves
    on rather than failing the whole report.
    """
    lines = ["## Retrieval window size and repeat-call variance", ""]
    lines.append(
        "Both analyses below required live model calls and are not recomputed by "
        "this script. They are embedded from the standalone runs already on disk."
    )
    lines.append("")

    if os.path.exists(N_SWEEP_PATH):
        sweep = pd.read_csv(N_SWEEP_PATH)
        lines.append("### Retrieval window size test (GPT-4o, type 2 diabetes register standard, zero-shot, RAG)")
        lines.append("")
        lines.append("| N | Precision | Recall | F1 | Fabricated identifiers (mean) |")
        lines.append("|---|---|---|---|---|")
        for _, r in sweep.iterrows():
            lines.append(
                f"| {int(r['n_results'])} | {r['precision_mean']:.3f} ± {r['precision_sd']:.3f} "
                f"| {r['recall_mean']:.3f} ± {r['recall_sd']:.3f} "
                f"| {r['f1_mean']:.3f} ± {r['f1_sd']:.3f} "
                f"| {r['fabricated_identifiers_mean']:.1f} |"
            )
        lines.append("")
    else:
        lines.append(f"*(no {N_SWEEP_PATH} found — skipped)*")
        lines.append("")

    if os.path.exists(PATH_BASELINE_PATH):
        with open(PATH_BASELINE_PATH) as f:
            baseline = json.load(f)
        lines.append("### Repeat-call variance (same prompt, 3 calls, one path at a time)")
        lines.append("")
        lines.append("| Model | Path | Pairwise overlaps (% of the smaller response) |")
        lines.append("|---|---|---|")
        for model, paths in baseline.get("summary", {}).items():
            for path_name in ("chatlas", "native"):
                if path_name not in paths:
                    continue
                sizes = paths[path_name]["sizes"]
                overlaps = paths[path_name]["pairwise_overlaps"]
                pairs = [(0, 1), (0, 2), (1, 2)]
                pcts = [
                    100 * ov / min(sizes[i], sizes[j])
                    for (i, j), ov in zip(pairs, overlaps)
                ]
                lines.append(f"| {model} | {path_name} | {', '.join(f'{p:.1f}%' for p in pcts)} |")
        lines.append("")
    else:
        lines.append(f"*(no {PATH_BASELINE_PATH} found — skipped)*")
        lines.append("")
    return lines


def build_chd_retrieval_check_section():
    """
    Two checks against the live retrieval corpus: whether the coronary
    heart disease anatomical-category codes exist in the knowledge base at
    all, and a hand-written multi-query retrieval test at both a
    size-matched (16 x N=25, pooled candidate set comparable to a single
    N=400 search) and an unmatched (16 x N=400) window. No language model
    is called at any point in this section — it measures what the search
    returns, not what a model would select from it. Needs
    pipeline_core.py's full retrieval stack (embedding model, ChromaDB,
    BM25 index), which is why this is gated behind --with-retrieval-checks
    rather than run by default.
    """
    import pipeline_core as pc

    lines = ["## Coronary heart disease retrieval check", ""]
    chd = pd.read_csv(CHD_GOLD_PATH, dtype={"code": str})
    gold_by_cat = {cat: set(chd[chd["category"] == cat]["code"]) for cat in chd["category"].unique()}
    gold_all = set(chd["code"])

    cat_a = chd[chd["category"] == "A"]
    result = pc.collection.get(ids=cat_a["code"].tolist())
    found = set(result["ids"])
    lines.append(f"Anatomical-category codes present in the live corpus: {len(found)}/{len(cat_a)}.")
    lines.append("")

    pooled_by_window = {}
    for n_per_search, key in [(25, "matched"), (400, "unmatched")]:
        pooled = set()
        for terms in CHD_MULTI_QUERY_SEARCH_TERMS.values():
            for term in terms:
                retrieved = pc.retrieve_hybrid(
                    term, pc.collection, pc.embedding_model, pc.bm25, pc.bm25_codes, n_results=n_per_search
                )
                pooled |= set(c["code"] for c in retrieved)
        pooled_by_window[key] = pooled

    single = pc.retrieve_hybrid(
        "Coronary Heart Disease", pc.collection, pc.embedding_model, pc.bm25, pc.bm25_codes, n_results=400
    )
    single_codes = set(c["code"] for c in single)

    lines.append(
        "| Category | Reference codes | Single search (N=400) "
        "| Multi-query, size-matched (16 x N=25) | Multi-query, unmatched (16 x N=400) |"
    )
    lines.append("|---|---|---|---|---|")
    category_labels = {
        "A": "Anatomical", "C": "Complication", "H": "History",
        "P": "Procedure/admin", "D": "Diagnosis", "S": "Subtype",
    }
    for cat_key, cat_label in category_labels.items():
        codes = gold_by_cat.get(cat_key, set())
        if not codes:
            continue
        single_pct = 100 * len(codes & single_codes) / len(codes)
        matched_pct = 100 * len(codes & pooled_by_window["matched"]) / len(codes)
        unmatched_pct = 100 * len(codes & pooled_by_window["unmatched"]) / len(codes)
        lines.append(f"| {cat_label} | {len(codes)} | {single_pct:.1f}% | {matched_pct:.1f}% | {unmatched_pct:.1f}% |")
    whole_single = 100 * len(gold_all & single_codes) / len(gold_all)
    whole_matched = 100 * len(gold_all & pooled_by_window["matched"]) / len(gold_all)
    whole_unmatched = 100 * len(gold_all & pooled_by_window["unmatched"]) / len(gold_all)
    lines.append(
        f"| Whole condition | {len(gold_all)} | {whole_single:.1f}% "
        f"| {whole_matched:.1f}% | {whole_unmatched:.1f}% |"
    )
    lines.append("")
    return lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--with-retrieval-checks",
        action="store_true",
        help="Also run the coronary heart disease retrieval check, which loads "
        "the full retrieval stack (embedding model, ChromaDB, BM25) and takes "
        "on the order of 20 extra seconds. Off by default so a normal run stays fast.",
    )
    args = parser.parse_args()

    models = find_model_folders(RESULTS_DIR)
    if not models:
        raise SystemExit(f"No model folders with pooled_metrics.csv found under {RESULTS_DIR}/")

    report_lines = ["# LLM Codelist Generation — Analysis Report", ""]
    report_lines += build_cross_model_table(models)
    report_lines += build_runtime_table(models)
    report_lines += build_statistical_treatment_section(models)
    report_lines += build_combined_per_condition_table(models)
    report_lines += build_f05_vs_f1_section(models)
    report_lines += build_fabrication_section(models)
    report_lines += build_external_precomputed_section()
    report_lines += build_sensitivity_section(models)
    if args.with_retrieval_checks:
        report_lines += build_chd_retrieval_check_section()

    for model_dir, (pooled_df, subtype_df, per_epoch_df, _, _) in models.items():
        model_label = pooled_df["model_label"].iloc[0]
        conditions = [c for c in pooled_df["condition"].unique() if "Audit" not in c]
        # Excludes T2DM's audit condition rows here too — those are a re-scoring
        # of the same generation, not a separate generation attempt, so counting
        # them would double-count T2DM's epochs in the failure-rate denominator.
        main_per_epoch_df = per_epoch_df[per_epoch_df["condition"].isin(conditions)]

        report_lines.append(f"## Model: {model_label}")
        report_lines.append("")
        report_lines += build_best_strategy_section(pooled_df, conditions, "rag", "Best RAG strategy per condition")
        report_lines += build_best_strategy_section(pooled_df, conditions, "non_rag", "Best non-RAG strategy per condition")
        report_lines += build_subtype_section(pooled_df, subtype_df, conditions)
        report_lines += build_audit_section(pooled_df)
        report_lines += build_flags_section(pooled_df, subtype_df, main_per_epoch_df, conditions)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        f.write("\n".join(report_lines))

    print(f"Wrote report to {OUTPUT_PATH} ({len(models)} model(s): {', '.join(models)})")


if __name__ == "__main__":
    main()
