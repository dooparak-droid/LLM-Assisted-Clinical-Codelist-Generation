# evaluate.py

"""
Evaluates LLM-generated SNOMED-CT codelists against gold standard codelists.

Three evaluation layers:
  1. Full-scope: all gold standard codes (original behaviour)
  2. Diagnosis-standardised: only D+S category codes, enabling fair
     cross-condition comparison despite scope differences
  3. Category-level recall breakdown: per-category recall (D, S, V, C, etc.)
     to understand which code types the LLM captures or misses

Also supports dual gold standard evaluation for T2DM (_cod vs _codaudit)
as a sensitivity analysis on gold standard breadth.

Computes precision, recall, F1, and F0.5 per experiment run (per-epoch),
then produces pooled summary statistics (mean and standard deviation)
across epochs for each condition × strategy × retrieval type combination.
"""

# Standard library
import json
import os

# Third party
import pandas as pd

# ── Configuration ──────────────────────────────────────────────

RESULTS_PATH = "results/raw_results.json"
GOLD_STANDARD_DIR = "data/categorised_gold_standards/"

# Optional post-processing: adds a 'term' column to retrieval_attribution.csv
# via enrich_attribution.py (looks codes up in the ChromaDB SNOMED store).
# Off by default — set to True to enable.
ENRICH_RETRIEVAL_ATTRIBUTION = False

# Primary gold standards — one per condition
GOLD_STANDARD_FILES = {
    "Type 2 Diabetes Mellitus": "dmtype2_cod_categorised.csv",
    "Asthma": "ast_cod_categorised.csv",
    "Atrial Fibrillation": "afib_cod_categorised.csv",
    "Hypothyroidism": "thy_cod_categorised.csv",
    "Multiple Sclerosis": "ms_cod_categorised.csv",
    "Polymyalgia Rheumatica": "pmr_cod_categorised.csv",
    "Coronary Heart Disease": "chd_cod_categorised.csv",
}

# Additional gold standards for sensitivity analysis.
# Each entry maps a label to a dict with the CSV filename and the
# condition name in raw_results.json that it should be matched against.
ADDITIONAL_GOLD_STANDARDS = {
    "Type 2 Diabetes Mellitus (audit)": {
        "file": "dmtype2audit_cod_categorised.csv",
        "matches_condition": "Type 2 Diabetes Mellitus",
    },
}

# Categories considered "diagnosis-equivalent" for the standardised layer
DIAGNOSIS_CATEGORIES = {"D", "S"}


# ── Load functions ──────────────────────────────────────────────


def load_gold_standards(gs_files, gs_dir):
    """
    Load all gold standard codelists from categorised CSV files.

    Returns:
        gold_standards: dict {condition: set of code strings}
        gold_standard_terms: dict {condition: {code: term}}
        gold_standard_categories: dict {condition: {code: category_letter}}
    """
    gold_standards = {}
    gold_standard_terms = {}
    gold_standard_categories = {}

    for condition, filename in gs_files.items():
        filepath = os.path.join(gs_dir, filename)
        df = pd.read_csv(filepath, dtype={"code": str})
        gold_standards[condition] = set(df["code"])
        gold_standard_terms[condition] = dict(zip(df["code"], df["term"]))
        gold_standard_categories[condition] = dict(zip(df["code"], df["category"]))
        print(f"  {condition}: {len(gold_standards[condition])} codes loaded")

    return gold_standards, gold_standard_terms, gold_standard_categories


def load_additional_gold_standards(additional_gs, gs_dir):
    """
    Load additional gold standards (e.g. T2DM audit) for sensitivity analysis.
    Returns the same triple of dicts as load_gold_standards.
    """
    gs_files = {label: info["file"] for label, info in additional_gs.items()}
    return load_gold_standards(gs_files, gs_dir)


def load_results(results_path):
    """
    Load raw experiment results from JSON.
    Returns a list of result dicts.
    """
    with open(results_path, "r") as f:
        return json.load(f)


# ── Core evaluation function ────────────────────────────────────


def compute_metrics(generated_codes, gold_codes, beta=1.0):
    """
    Compare a generated codelist against a gold standard.

    Args:
        generated_codes: list of dicts with 'code' key, OR a set of code strings.
        gold_codes: set of code strings.
        beta: F-beta parameter (1.0 = F1, 0.5 = F0.5).
    """
    # Accept either list-of-dicts or set-of-strings
    if isinstance(generated_codes, set):
        generated_set = generated_codes
    else:
        generated_set = set([c["code"] for c in generated_codes])

    true_positives = generated_set & gold_codes
    false_positives = generated_set - gold_codes
    false_negatives = gold_codes - generated_set

    if len(generated_set) == 0:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f_beta": 0.0,
            "true_positives": 0,
            "false_positives": 0,
            "false_negatives": len(gold_codes),
            "generated_count": 0,
            "gold_count": len(gold_codes),
            "size_ratio": 0.0,
        }

    precision = len(true_positives) / len(generated_set)
    recall = len(true_positives) / len(gold_codes) if len(gold_codes) > 0 else 0.0

    if precision + recall == 0:
        f_beta = 0.0
    else:
        f_beta = (1 + beta**2) * (precision * recall) / ((beta**2 * precision) + recall)

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f_beta": round(f_beta, 4),
        "true_positives": len(true_positives),
        "false_positives": len(false_positives),
        "false_negatives": len(false_negatives),
        "generated_count": len(generated_set),
        "gold_count": len(gold_codes),
        "size_ratio": round(
            len(generated_set) / len(gold_codes) if len(gold_codes) > 0 else 0, 4
        ),
    }


# ── Helper: filter gold standard by categories ──────────────────


def filter_codes_by_categories(gold_codes, categories_map, include_categories):
    """
    Return the subset of gold_codes whose category is in include_categories.

    Args:
        gold_codes: set of code strings (full gold standard)
        categories_map: dict {code: category_letter} for this condition
        include_categories: set of category letters to keep, e.g. {"D", "S"}

    Returns:
        set of code strings matching the requested categories
    """
    return {
        code for code in gold_codes if categories_map.get(code) in include_categories
    }


# ── Layer 1: Full-scope per-epoch evaluation ─────────────────────


def evaluate_per_epoch(results, gold_standards, betas=(1.0, 0.5)):
    """
    Compute metrics for every individual experiment run (one row per
    condition × strategy × retrieval_type × epoch).

    This is the FULL-SCOPE evaluation — all gold standard codes included.
    """
    rows = []

    for r in results:
        if not r["success"]:
            continue

        condition = r["condition"]
        gold_codes = gold_standards[condition]

        row = {
            "condition": condition,
            "strategy": r["strategy"],
            "retrieval_type": r["retrieval_type"],
            "epoch": r["epoch"],
            "scope": "full",
        }

        base_metrics = compute_metrics(r["generated_codes"], gold_codes, beta=1.0)
        row["precision"] = base_metrics["precision"]
        row["recall"] = base_metrics["recall"]
        row["true_positives"] = base_metrics["true_positives"]
        row["false_positives"] = base_metrics["false_positives"]
        row["false_negatives"] = base_metrics["false_negatives"]
        row["generated_count"] = base_metrics["generated_count"]
        row["gold_count"] = base_metrics["gold_count"]
        row["size_ratio"] = base_metrics["size_ratio"]

        for beta in betas:
            metrics = compute_metrics(r["generated_codes"], gold_codes, beta=beta)
            beta_label = "f1" if beta == 1.0 else f"f{beta}".replace(".", "")
            row[beta_label] = metrics["f_beta"]

        rows.append(row)

    return pd.DataFrame(rows)


# ── Layer 2: Diagnosis-standardised (D+S) per-epoch evaluation ───


def evaluate_per_epoch_diagnosis_standardised(
    results, gold_standards, gold_standard_categories, betas=(1.0, 0.5)
):
    """
    Compute metrics using only D+S codes from the gold standard.

    The generated codelist is intersected with the D+S gold subset for
    precision; recall is computed against the D+S subset only.
    This enables fairer cross-condition comparison by removing scope
    differences caused by complications, anatomical detail, etc.
    """
    rows = []

    for r in results:
        if not r["success"]:
            continue

        condition = r["condition"]
        categories_map = gold_standard_categories[condition]

        # Filter gold standard to D+S only
        ds_gold_codes = filter_codes_by_categories(
            gold_standards[condition], categories_map, DIAGNOSIS_CATEGORIES
        )

        if len(ds_gold_codes) == 0:
            continue  # skip if no D/S codes (shouldn't happen)

        # Filter generated codes to only those that MATCH a D+S gold code
        # or are false positives. For precision in D+S context, we consider
        # the full generated set vs the D+S gold — a generated code that
        # matches a C/V/A/H/P gold code is a false positive in this scope.
        generated_set = set(c["code"] for c in r["generated_codes"])

        row = {
            "condition": condition,
            "strategy": r["strategy"],
            "retrieval_type": r["retrieval_type"],
            "epoch": r["epoch"],
            "scope": "diagnosis_standardised",
        }

        # Metrics: generated set vs D+S gold subset
        base_metrics = compute_metrics(generated_set, ds_gold_codes, beta=1.0)
        row["precision"] = base_metrics["precision"]
        row["recall"] = base_metrics["recall"]
        row["true_positives"] = base_metrics["true_positives"]
        row["false_positives"] = base_metrics["false_positives"]
        row["false_negatives"] = base_metrics["false_negatives"]
        row["generated_count"] = base_metrics["generated_count"]
        row["gold_count"] = base_metrics["gold_count"]
        row["size_ratio"] = base_metrics["size_ratio"]

        for beta in betas:
            metrics = compute_metrics(generated_set, ds_gold_codes, beta=beta)
            beta_label = "f1" if beta == 1.0 else f"f{beta}".replace(".", "")
            row[beta_label] = metrics["f_beta"]

        rows.append(row)

    return pd.DataFrame(rows)


# ── Layer 3: Category-level recall breakdown ─────────────────────


def evaluate_category_recall(results, gold_standards, gold_standard_categories):
    """
    For each experiment run, compute recall broken down by code category
    (D, S, V, C, A, H, P). This reveals which types of codes the LLM
    captures well vs. misses.

    Returns:
        DataFrame with columns: condition, strategy, retrieval_type, epoch,
        category, category_gold_count, category_tp, category_recall
    """
    rows = []

    for r in results:
        if not r["success"]:
            continue

        condition = r["condition"]
        categories_map = gold_standard_categories[condition]
        generated_set = set(c["code"] for c in r["generated_codes"])

        # Get the set of categories present in this gold standard
        present_categories = set(categories_map.values())

        for cat in sorted(present_categories):
            # Gold codes in this category
            cat_gold = {code for code, c in categories_map.items() if c == cat}
            cat_tp = generated_set & cat_gold
            cat_recall = len(cat_tp) / len(cat_gold) if len(cat_gold) > 0 else 0.0

            rows.append(
                {
                    "condition": condition,
                    "strategy": r["strategy"],
                    "retrieval_type": r["retrieval_type"],
                    "epoch": r["epoch"],
                    "category": cat,
                    "category_gold_count": len(cat_gold),
                    "category_tp": len(cat_tp),
                    "category_recall": round(cat_recall, 4),
                }
            )

    return pd.DataFrame(rows)


# ── Pooled summary across epochs ─────────────────────────────────


def pool_across_epochs(per_epoch_df):
    """
    Average metrics across epochs for each condition × strategy × retrieval_type
    combination. Returns mean and standard deviation for each metric.

    Args:
        per_epoch_df: DataFrame from evaluate_per_epoch() or
                      evaluate_per_epoch_diagnosis_standardised()

    Returns:
        pandas DataFrame, one row per condition × strategy × retrieval_type.
    """
    metric_columns = ["precision", "recall", "f1", "f05"]

    # Include scope in groupby if the column exists
    group_cols = ["condition", "strategy", "retrieval_type"]
    if "scope" in per_epoch_df.columns:
        group_cols.append("scope")

    pooled = per_epoch_df.groupby(group_cols)[metric_columns].agg(["mean", "std"])

    # Flatten the multi-level column names (e.g. ('precision', 'mean') -> 'precision_mean')
    pooled.columns = ["_".join(col) for col in pooled.columns]
    pooled = pooled.reset_index()

    # Also record how many epochs actually contributed (in case some failed)
    n_epochs = per_epoch_df.groupby(group_cols).size().reset_index(name="n_epochs")
    pooled = pooled.merge(n_epochs, on=group_cols)

    return pooled


def pool_category_recall(category_df):
    """
    Average category-level recall across epochs.

    Returns:
        DataFrame with mean and std of category_recall, grouped by
        condition × strategy × retrieval_type × category.
    """
    group_cols = ["condition", "strategy", "retrieval_type", "category"]

    pooled = (
        category_df.groupby(group_cols)
        .agg(
            category_gold_count=(
                "category_gold_count",
                "first",
            ),  # constant across epochs
            category_recall_mean=("category_recall", "mean"),
            category_recall_std=("category_recall", "std"),
            n_epochs=("category_recall", "size"),
        )
        .reset_index()
    )

    return pooled


# ── Qualitative evaluation ─────────────────────────────────


def evaluate_code_breakdown(
    results, gold_standards, gold_standard_terms, gold_standard_categories=None
):
    """
    Produce a long-format table with one row per individual code,
    categorised as true_positive, false_positive, or false_negative,
    for qualitative review (e.g. open-world problem analysis).

    If gold_standard_categories is provided, includes the gold standard
    category (D/S/V/C/A/H/P) for true positives and false negatives.

    Returns:
        pandas DataFrame with columns: condition, strategy, retrieval_type,
        epoch, eval_category, code, term, [gold_category].
    """
    rows = []

    for r in results:
        if not r["success"]:
            continue

        condition = r["condition"]
        gold_codes = gold_standards[condition]
        gold_terms = gold_standard_terms[condition]
        cat_map = (
            gold_standard_categories.get(condition, {})
            if gold_standard_categories
            else {}
        )

        # Build a code -> term lookup from the generated codes
        generated_lookup = {c["code"]: c["term"] for c in r["generated_codes"]}
        generated_set = set(generated_lookup.keys())

        true_positives = generated_set & gold_codes
        false_positives = generated_set - gold_codes
        false_negatives = gold_codes - generated_set

        base_info = {
            "condition": condition,
            "strategy": r["strategy"],
            "retrieval_type": r["retrieval_type"],
            "epoch": r["epoch"],
        }

        for code in true_positives:
            rows.append(
                {
                    **base_info,
                    "eval_category": "true_positive",
                    "code": code,
                    "term": generated_lookup[code],
                    "gold_category": cat_map.get(code, ""),
                }
            )

        for code in false_positives:
            rows.append(
                {
                    **base_info,
                    "eval_category": "false_positive",
                    "code": code,
                    "term": generated_lookup[code],
                    "gold_category": "",  # not in gold standard
                }
            )

        for code in false_negatives:
            rows.append(
                {
                    **base_info,
                    "eval_category": "false_negative",
                    "code": code,
                    "term": gold_terms[code],
                    "gold_category": cat_map.get(code, ""),
                }
            )

    return pd.DataFrame(rows)


def evaluate_retrieval_attribution(results, gold_standards):
    """
    For RAG results only, classify each false negative as either a
    retrieval failure (code never made it into retrieved_codes) or a
    generation failure (code was retrieved but the LLM didn't include it).

    Returns:
        pandas DataFrame with columns: condition, strategy, epoch, code,
        failure_type ('retrieval_failure' or 'generation_failure').
    """
    rows = []

    for r in results:
        if not r["success"]:
            continue
        if r["retrieval_type"] != "rag":
            continue

        condition = r["condition"]
        gold_codes = gold_standards[condition]

        generated_set = set([c["code"] for c in r["generated_codes"]])
        retrieved_set = set(r["retrieved_codes"])

        false_negatives = gold_codes - generated_set

        for code in false_negatives:
            failure_type = (
                "generation_failure" if code in retrieved_set else "retrieval_failure"
            )

            rows.append(
                {
                    "condition": condition,
                    "strategy": r["strategy"],
                    "epoch": r["epoch"],
                    "code": code,
                    "failure_type": failure_type,
                }
            )

    return pd.DataFrame(rows)


# ── Dual gold standard evaluation (T2DM sensitivity analysis) ────


def evaluate_additional_gold_standards(
    results, additional_gs_config, gs_dir, betas=(1.0, 0.5)
):
    """
    Evaluate experiment results against additional gold standards.

    For each entry in additional_gs_config, finds results matching
    'matches_condition' and evaluates them against the alternative
    gold standard. This enables sensitivity analysis (e.g. T2DM
    _cod vs _codaudit).

    Returns:
        per_epoch_df: DataFrame with the same schema as evaluate_per_epoch,
                      but with the alternative gold standard label as condition.
    """
    add_gs, add_gs_terms, add_gs_cats = load_additional_gold_standards(
        additional_gs_config, gs_dir
    )

    rows = []

    for label, info in additional_gs_config.items():
        source_condition = info["matches_condition"]
        gold_codes = add_gs[label]

        for r in results:
            if not r["success"]:
                continue
            if r["condition"] != source_condition:
                continue

            row = {
                "condition": label,  # e.g. "Type 2 Diabetes Mellitus (audit)"
                "strategy": r["strategy"],
                "retrieval_type": r["retrieval_type"],
                "epoch": r["epoch"],
                "scope": "full",
            }

            base_metrics = compute_metrics(r["generated_codes"], gold_codes, beta=1.0)
            row["precision"] = base_metrics["precision"]
            row["recall"] = base_metrics["recall"]
            row["true_positives"] = base_metrics["true_positives"]
            row["false_positives"] = base_metrics["false_positives"]
            row["false_negatives"] = base_metrics["false_negatives"]
            row["generated_count"] = base_metrics["generated_count"]
            row["gold_count"] = base_metrics["gold_count"]
            row["size_ratio"] = base_metrics["size_ratio"]

            for beta in betas:
                metrics = compute_metrics(r["generated_codes"], gold_codes, beta=beta)
                beta_label = "f1" if beta == 1.0 else f"f{beta}".replace(".", "")
                row[beta_label] = metrics["f_beta"]

            rows.append(row)

    return pd.DataFrame(rows)


# ── Run it ───────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Loading results and gold standards...")
    results = load_results(RESULTS_PATH)
    gold_standards, gold_standard_terms, gold_standard_categories = load_gold_standards(
        GOLD_STANDARD_FILES, GOLD_STANDARD_DIR
    )

    # ── Layer 1: Full-scope evaluation ──────────────────────────
    print("\n=== Layer 1: Full-scope evaluation ===")
    print("Computing per-epoch metrics...")
    per_epoch_df = evaluate_per_epoch(results, gold_standards)

    print("Pooling across epochs...")
    pooled_df = pool_across_epochs(per_epoch_df)

    # ── Layer 2: Diagnosis-standardised (D+S) evaluation ────────
    print("\n=== Layer 2: Diagnosis-standardised (D+S) evaluation ===")
    print("Computing D+S per-epoch metrics...")
    ds_per_epoch_df = evaluate_per_epoch_diagnosis_standardised(
        results, gold_standards, gold_standard_categories
    )

    print("Pooling D+S across epochs...")
    ds_pooled_df = pool_across_epochs(ds_per_epoch_df)

    # ── Layer 3: Category-level recall breakdown ────────────────
    print("\n=== Layer 3: Category-level recall breakdown ===")
    print("Computing category-level recall...")
    category_df = evaluate_category_recall(
        results, gold_standards, gold_standard_categories
    )

    print("Pooling category recall across epochs...")
    category_pooled_df = pool_category_recall(category_df)

    # ── Qualitative evaluation ──────────────────────────────────
    print("\nEvaluating code breakdown...")
    code_breakdown_df = evaluate_code_breakdown(
        results, gold_standards, gold_standard_terms, gold_standard_categories
    )

    print("Evaluating retrieval attribution...")
    rag_df = evaluate_retrieval_attribution(results, gold_standards)

    # ── T2DM dual gold standard sensitivity analysis ────────────
    print("\n=== T2DM dual gold standard sensitivity analysis ===")
    additional_per_epoch_df = evaluate_additional_gold_standards(
        results, ADDITIONAL_GOLD_STANDARDS, GOLD_STANDARD_DIR
    )
    if len(additional_per_epoch_df) > 0:
        additional_pooled_df = pool_across_epochs(additional_per_epoch_df)
    else:
        additional_pooled_df = pd.DataFrame()

    # ── Save all tables ─────────────────────────────────────────
    os.makedirs("results", exist_ok=True)

    # Layer 1
    per_epoch_df.to_csv("results/per_epoch_metrics.csv", index=False)
    pooled_df.to_csv("results/pooled_metrics.csv", index=False)

    # Layer 2
    ds_per_epoch_df.to_csv("results/per_epoch_metrics_ds.csv", index=False)
    ds_pooled_df.to_csv("results/pooled_metrics_ds.csv", index=False)

    # Layer 3
    category_df.to_csv("results/category_recall_per_epoch.csv", index=False)
    category_pooled_df.to_csv("results/category_recall_pooled.csv", index=False)

    # Qualitative
    code_breakdown_df.to_csv("results/code_breakdown_metrics.csv", index=False)
    rag_df.to_csv("results/retrieval_attribution.csv", index=False)

    # T2DM sensitivity
    if len(additional_per_epoch_df) > 0:
        additional_per_epoch_df.to_csv(
            "results/per_epoch_metrics_t2dm_audit.csv", index=False
        )
        additional_pooled_df.to_csv(
            "results/pooled_metrics_t2dm_audit.csv", index=False
        )

    # ── Print summaries ─────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"LAYER 1 — Full-scope:")
    print(f"  Per-epoch: {len(per_epoch_df)} rows → results/per_epoch_metrics.csv")
    print(f"  Pooled:    {len(pooled_df)} rows → results/pooled_metrics.csv")

    print(f"\nLAYER 2 — Diagnosis-standardised (D+S):")
    print(
        f"  Per-epoch: {len(ds_per_epoch_df)} rows → results/per_epoch_metrics_ds.csv"
    )
    print(f"  Pooled:    {len(ds_pooled_df)} rows → results/pooled_metrics_ds.csv")

    print(f"\nLAYER 3 — Category-level recall:")
    print(
        f"  Per-epoch: {len(category_df)} rows → results/category_recall_per_epoch.csv"
    )
    print(
        f"  Pooled:    {len(category_pooled_df)} rows → results/category_recall_pooled.csv"
    )

    print(f"\nQualitative:")
    print(
        f"  Code breakdown:          {len(code_breakdown_df)} rows → results/code_breakdown_metrics.csv"
    )
    print(
        f"  Retrieval attribution:   {len(rag_df)} rows → results/retrieval_attribution.csv"
    )

    if len(additional_per_epoch_df) > 0:
        print(f"\nT2DM sensitivity analysis:")
        print(
            f"  Per-epoch: {len(additional_per_epoch_df)} rows → results/per_epoch_metrics_t2dm_audit.csv"
        )
        print(
            f"  Pooled:    {len(additional_pooled_df)} rows → results/pooled_metrics_t2dm_audit.csv"
        )

    print(f"\n{'='*60}")
    print("\nPooled summary (full-scope):")
    print(pooled_df.to_string(index=False))

    if len(additional_pooled_df) > 0:
        print("\nPooled summary (T2DM audit gold standard):")
        print(additional_pooled_df.to_string(index=False))

    # ── Optional: enrich retrieval attribution with SNOMED terms ────
    if ENRICH_RETRIEVAL_ATTRIBUTION:
        from enrich_attribution import enrich_retrieval_attribution

        print(f"\n{'='*60}")
        print("Enriching retrieval attribution with SNOMED terms...")
        enrich_retrieval_attribution()
