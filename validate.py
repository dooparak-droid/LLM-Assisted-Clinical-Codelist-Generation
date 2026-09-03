# validate.py

"""
Standalone smoke-test script — runs the same experiment combination across
multiple (provider, model) configs, to confirm each one returns a valid
codelist before trusting it in the real pipeline.

Importing experiment_runner triggers its module-level setup (gold standards,
ChromaDB collection, embedding model, BM25 index) but NOT run_full_experiment()
or save_results() — those only run under experiment_runner's own
`if __name__ == "__main__"` guard. This script calls run_single_experiment()
directly and only prints results; results/raw_results.json is never opened
or written.
"""

import json
import experiment_runner as er

CONDITION = "Type 2 Diabetes Mellitus"  # exact key from er.CONDITIONS
STRATEGY = "zero_shot"
RETRIEVAL_TYPE = "non_rag"
EPOCH = 1

# Add/remove entries here to smoke-test more (provider, model) configs.
# base_url=None uses each provider's default endpoint (e.g. Ollama's local
# http://localhost:11434).
#
# Default kept cheap/fast (gpt-4o-2024-08-06) so routine smoke-test runs
# don't spend on frontier models by default. Uncomment specific MODELS
# entries below when you actually need to re-validate a Tier 1/2 pick
# (e.g. after a code change, or before a real full run).
#
# Known results so far (see chat history for full detail):
#   - GPT-5.5: PASS. Required the temperature-fallback fix in call_llm()
#     (reasoning-tier models reject non-default temperature outright).
#   - gemini-3.1-pro-preview / gemini-2.5-pro: FAIL — free-tier quota is
#     literally 0 for BOTH on this account. No Pro-tier Gemini model is free
#     here, at any generation — needs billing enabled on the Google Cloud
#     project before either can be smoke-tested for real.
#   - gemini-2.5-flash: FAIL — 404, retired for new API keys/users entirely
#     (unrelated to tier/billing; the model itself is gone for this account).
#   - gemini-3.1-flash-lite: PASS, smoke-tested successfully (current-gen,
#     low-cost tier, already the real Tier 2 pick in er.MODELS).
#   - MedGemma 4B (Ollama): PASS, smoke-tested successfully.
SMOKE_TEST_MODELS = [
    {"label": "OpenAI (default)", "provider": er.PROVIDER, "model": er.MODEL, "base_url": None},
    next(m for m in er.MODELS if m["label"] == "GPT-5.4-mini"),
    # next(m for m in er.MODELS if m["label"] == "Gemini 3.1 Flash-Lite"),  # already smoke-tested
    # next(m for m in er.MODELS if m["label"] == "GPT-5.5"),
    # next(m for m in er.MODELS if m["label"] == "Gemini 3.1 Pro"),  # needs billing enabled first
    # {"label": "MedGemma 4B (Ollama)", "provider": "ollama", "model": "medgemma:4b", "base_url": None},
]


def validate_codes(generated_codes):
    """
    Confirm generated_codes is a list of {"code", "term"} string-pair dicts.
    Returns (is_valid, reason). reason is None when valid.
    """
    if not isinstance(generated_codes, list):
        return False, "generated_codes is not a list"
    for item in generated_codes:
        if not isinstance(item, dict) or "code" not in item or "term" not in item:
            return False, f"malformed entry: {item!r}"
        if not isinstance(item["code"], str) or not isinstance(item["term"], str):
            return False, f"'code'/'term' not strings: {item!r}"
    return True, None


results_summary = []

for model_config in SMOKE_TEST_MODELS:
    label = model_config["label"]
    print(f"\n{'='*60}")
    print(f"Smoke test: {label}")
    print(
        f"  {CONDITION} | {STRATEGY} | {RETRIEVAL_TYPE} | epoch {EPOCH} "
        f"| provider={model_config['provider']} | model={model_config['model']}"
    )

    result = er.run_single_experiment(
        CONDITION,
        STRATEGY,
        RETRIEVAL_TYPE,
        EPOCH,
        er.collection,
        er.embedding_model,
        er.bm25,
        er.bm25_codes,
        provider=model_config["provider"],
        model=model_config["model"],
        base_url=model_config.get("base_url"),
    )

    schema_ok, schema_error = validate_codes(result["generated_codes"])
    passed = result["success"] and schema_ok

    print("\n--- Full result dict ---")
    print(json.dumps(result, indent=2))

    print("\n--- Summary ---")
    print(f"success:            {result['success']}")
    print(f"error_message:      {result['error_message']}")
    print(f"n_attempts:         {result.get('n_attempts')}")
    print(f"temperature_applied:{result.get('temperature_applied')}")
    print(f"n_generated_codes:  {len(result['generated_codes'])}")
    print(f"n_retrieved:        {result['n_retrieved']}")
    print(f"schema_valid:       {schema_ok}" + (f" ({schema_error})" if schema_error else ""))
    print(f"PASS/FAIL:          {'PASS' if passed else 'FAIL'}")

    print("\n--- raw_text (last attempt) ---")
    print(result.get("raw_text"))

    results_summary.append({"label": label, "passed": passed})

print(f"\n{'='*60}")
print("Smoke test summary:")
for r in results_summary:
    print(f"  [{'PASS' if r['passed'] else 'FAIL'}] {r['label']}")
