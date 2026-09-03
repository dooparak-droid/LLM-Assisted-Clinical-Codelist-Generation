# Script description

"""
experiment_runner.py

Orchestrates LLM-based SNOMED-CT codelist generation experiments across
multiple clinical conditions, prompting strategies (zero-shot, few-shot,
chain-of-thought), and retrieval conditions (RAG using SNOMED-CT via
ChromaDB, vs. non-RAG / parametric knowledge only).

Each unique combination of condition × strategy × retrieval type × model is
run for EPOCHS repetitions. Results are saved incrementally to RESULTS_PATH
after every API call to prevent data loss on failure or interruption.
Already-completed (successful) combinations are skipped on rerun.

Shared logic (config, retrieval stack, prompt builders, gold standard
loading, chatlas call logic) lives in pipeline_core.py and is imported from
there — this file is orchestration only. inspect_pipeline.py (the Inspect AI
harness) imports the same pipeline_core.py rather than importing from this
file, so neither runner duplicates or depends on the other.

Evaluation (precision/recall/F1) against gold standard codelists is
handled separately in evaluate.py.
"""

# Standard library
import os  # for file paths
import json  # for JSON parsing
import itertools  # for product() function
import datetime as dt  # we want to timestamp each result

import pipeline_core as pc

RESULTS_PATH = "results/raw_results.json"


# ── Single experiment runner ────────────────────────────────────


def run_single_experiment(
    condition,
    strategy,
    retrieval_type,
    epoch,
    collection,
    embedding_model,
    bm25,
    bm25_codes,
    provider=pc.PROVIDER,
    model=pc.MODEL,
    base_url=pc.BASE_URL,
):
    """
    Run one experiment: one condition × one strategy × one retrieval type ×
    one epoch × one (provider, model). Returns a dict containing all inputs,
    outputs, and metadata.
    """
    # Step 1: get retrieved concepts if this is a RAG run, otherwise None
    retrieved_concepts = None
    if retrieval_type == "rag":
        retrieved_concepts = pc.retrieve_hybrid(
            condition,
            collection,
            embedding_model,
            bm25,
            bm25_codes,
            n_results=pc.N_RESULTS,
        )

    # Step 2: pick the right prompt builder function based on strategy
    prompt_builder = pc.PROMPT_BUILDERS[strategy]
    user_content = prompt_builder(condition, retrieved_concepts)

    # Step 3: call the LLM (provider-agnostic via chatlas), with retries on
    # malformed/incomplete JSON, transient API errors, or unsupported
    # temperature (retried without it)
    codes, raw_text, n_attempts, error_message, temperature_applied = pc.call_llm(
        user_content,
        provider=provider,
        model=model,
        base_url=base_url,
        max_retries=pc.MAX_RETRIES,
    )
    success = codes is not None

    # Step 4: package the result
    result = {
        "condition": condition,
        "strategy": strategy,
        "retrieval_type": retrieval_type,
        "epoch": epoch,
        "provider": provider,
        "model": model,
        "generated_codes": codes if success else [],
        "success": success,
        "error_message": error_message,
        "n_attempts": n_attempts,
        "temperature_applied": temperature_applied,
        "raw_text": raw_text,
        "n_retrieved": len(retrieved_concepts) if retrieved_concepts else 0,
        "retrieved_codes": (
            [c["code"] for c in retrieved_concepts] if retrieved_concepts else []
        ),
        "timestamp": dt.datetime.now().isoformat(),
    }

    return result


# ── Checkpointing ────────────────────────────────────────────────


def load_existing_results(results_path):
    """
    Load previously saved results if the file exists, otherwise return an empty list.
    """
    if os.path.exists(results_path):
        with open(results_path, "r") as f:
            return json.load(f)
    return []


def already_completed(
    existing_results, condition, strategy, retrieval_type, epoch, provider, model
):
    """
    Check whether this exact combination (including provider/model) has
    already been run successfully. provider/model are part of the match key
    so completed runs for one model never cause a different model's run of
    the same condition/strategy/retrieval_type/epoch to be skipped.
    """
    for r in existing_results:
        if (
            r["condition"] == condition
            and r["strategy"] == strategy
            and r["retrieval_type"] == retrieval_type
            and r["epoch"] == epoch
            and r.get("provider") == provider
            and r["model"] == model
            and r["success"] == True
        ):  # only skip if it succeeded — why? --  because we want to skip already-completed runs
            return True
    return False


def save_results(results, results_path):
    """
    Save the full results list to disk, overwriting the previous file.
    """
    os.makedirs(os.path.dirname(results_path), exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)


# ── Main experiment loop ────────────────────────────────────────


def run_full_experiment():
    """
    Run the complete experiment: every combination of condition × strategy ×
    retrieval type × epoch × model (from pc.MODELS). Skips combinations
    already completed successfully.
    """
    # Load what's already been done, if anything
    existing_results = load_existing_results(RESULTS_PATH)
    results = existing_results.copy()

    total_combinations = (
        len(pc.CONDITIONS)
        * len(pc.STRATEGIES)
        * len(pc.RETRIEVAL_TYPES)
        * pc.EPOCHS
        * len(pc.MODELS)
    )
    completed_count = 0
    skipped_count = 0

    print(f"Starting experiment: {total_combinations} total combinations\n")

    for condition, strategy, retrieval_type, epoch, model_config in itertools.product(
        pc.CONDITIONS, pc.STRATEGIES, pc.RETRIEVAL_TYPES, range(1, pc.EPOCHS + 1), pc.MODELS
    ):
        provider = model_config["provider"]
        model = model_config["model"]
        base_url = model_config.get("base_url")

        # Skip if already done
        if already_completed(
            results, condition, strategy, retrieval_type, epoch, provider, model
        ):
            skipped_count += 1
            continue

        print(
            f"Running: {condition} | {strategy} | {retrieval_type} | epoch {epoch} | {model_config['label']}"
        )

        result = run_single_experiment(
            condition,
            strategy,
            retrieval_type,
            epoch,
            pc.collection,
            pc.embedding_model,
            pc.bm25,
            pc.bm25_codes,
            provider=provider,
            model=model,
            base_url=base_url,
        )

        results.append(result)
        save_results(
            results, RESULTS_PATH
        )  # save after EVERY call — why? To avoid losing progress if there's a crash or an error

        completed_count += 1
        if not result["success"]:
            print(f"  FAILED: {result['error_message']}")

    print(f"\nDone. {completed_count} new runs completed, {skipped_count} skipped.")
    return results


# ── Run it ───────────────────────────────────────────────────────
if __name__ == "__main__":
    results = run_full_experiment()
