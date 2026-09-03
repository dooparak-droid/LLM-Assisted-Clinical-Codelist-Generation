# enrich_attribution.py

"""
Post-processing script: enriches results/retrieval_attribution.csv with the
SNOMED-CT preferred description ('term') for each code, looked up from the
same ChromaDB store used for retrieval (data/snomed/chroma_db/).

Standalone from evaluate.py by design — run directly, or call
enrich_retrieval_attribution() from evaluate.py behind a flag.
"""

# Standard library
import os

# Third party
import pandas as pd
import chromadb

# ── Configuration ──────────────────────────────────────────────

INPUT_PATH = "results/retrieval_attribution.csv"
OUTPUT_PATH = "results/retrieval_attribution_terms.csv"
CHROMA_PATH = "data/snomed/chroma_db"
CHROMA_COLLECTION = "snomed_concepts"
UNKNOWN_TERM = "unknown"
BATCH_SIZE = 5000  # chunk size for ChromaDB get() calls


def lookup_terms(codes, chroma_path=CHROMA_PATH, collection_name=CHROMA_COLLECTION):
    """
    Look up the SNOMED-CT term for each code in ChromaDB.

    Args:
        codes: list of unique code strings to look up.

    Returns:
        dict {code: term}. Codes not found in ChromaDB are omitted here —
        the caller fills those with UNKNOWN_TERM.
    """
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection(name=collection_name)

    code_to_term = {}
    for i in range(0, len(codes), BATCH_SIZE):
        batch = codes[i : i + BATCH_SIZE]
        results = collection.get(ids=batch)
        for code, term in zip(results["ids"], results["documents"]):
            code_to_term[code] = term

    return code_to_term


def enrich_retrieval_attribution(
    input_path=INPUT_PATH,
    output_path=OUTPUT_PATH,
    chroma_path=CHROMA_PATH,
    collection_name=CHROMA_COLLECTION,
):
    """
    Load retrieval_attribution.csv, add a 'term' column (right after 'code')
    with each code's SNOMED-CT preferred description, and save the result.
    Codes not found in ChromaDB get UNKNOWN_TERM rather than failing.
    """
    df = pd.read_csv(input_path, dtype={"code": str})

    unique_codes = df["code"].unique().tolist()
    print(f"Looking up {len(unique_codes)} unique codes in ChromaDB...")
    code_to_term = lookup_terms(unique_codes, chroma_path, collection_name)

    n_missing = len(unique_codes) - len(code_to_term)
    if n_missing > 0:
        print(f"  {n_missing} code(s) not found in ChromaDB — filled with '{UNKNOWN_TERM}'")

    term_column = df["code"].map(code_to_term).fillna(UNKNOWN_TERM)
    df.insert(df.columns.get_loc("code") + 1, "term", term_column)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"Saved enriched attribution: {len(df)} rows -> {output_path}")

    return df


if __name__ == "__main__":
    enrich_retrieval_attribution()
