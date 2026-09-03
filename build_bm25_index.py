# build_bm25_index.py

"""
One-time script to build a BM25 index over the SNOMED-CT corpus, using the
exact same source text already stored in ChromaDB (retrieved via
collection.get()) to guarantee both retrieval methods describe the same
document set. Persists the index to disk via pickle for reuse by
experiment_runner.py.
"""

import pickle
import chromadb
from rank_bm25 import BM25Okapi

CHROMA_PATH = "data/snomed/chroma_db"
BM25_OUTPUT_PATH = "data/snomed/bm25_index.pkl"


def load_corpus_from_chroma(chroma_path, batch_size=10000):
    """
    Pull all codes and terms directly out of the existing ChromaDB collection,
    paginating in batches to avoid exceeding the underlying database's
    SQL variable limit on a single query.
    """
    client = chromadb.PersistentClient(path=chroma_path)
    collection = client.get_collection(name="snomed_concepts")

    total_count = collection.count()
    print(
        f"Pulling all {total_count} documents from ChromaDB in batches of {batch_size}..."
    )

    codes = []
    terms = []
    offset = 0

    while offset < total_count:
        batch = collection.get(limit=batch_size, offset=offset)
        codes.extend(batch["ids"])
        terms.extend(batch["documents"])
        offset += batch_size
        print(f"  Fetched {len(codes)}/{total_count}...")

    return codes, terms


def build_bm25_index(terms):
    """
    Tokenise each term description and build a BM25Okapi index.
    """
    print("Tokenising corpus...")
    # Simple whitespace tokenisation, lowercased for case-insensitive matching
    tokenised_corpus = [term.lower().split() for term in terms]

    print("Building BM25 index...")
    bm25 = BM25Okapi(tokenised_corpus)

    return bm25


def save_bm25_index(bm25, codes, output_path):
    """
    Persist the BM25 index AND the corresponding codes list to disk.
    Both are needed together — BM25 only knows document POSITIONS,
    not which SNOMED code each position corresponds to.
    """
    with open(output_path, "wb") as f:
        pickle.dump({"bm25": bm25, "codes": codes}, f)
    print(f"Saved BM25 index to {output_path}")


if __name__ == "__main__":
    codes, terms = load_corpus_from_chroma(CHROMA_PATH)
    bm25_index = build_bm25_index(terms)
    save_bm25_index(bm25_index, codes, BM25_OUTPUT_PATH)
