"""
Sentinel — Precompute Retriever Embedding Cache

Build-time script. Enumerates the literature retriever's query space by
running every synthetic patient through the model + retriever's tag
extraction logic, collects every distinct query string that arises,
embeds each one, and saves the cache to disk.

At runtime, the deployed retriever loads this JSON cache and does
dict lookups — no sentence-transformers, no ChromaDB, no embedder
resident in memory.

Run this whenever:
  - You change FEATURE_TO_TAGS in literature_retriever.py
  - You retrain the model (different SHAP outputs → different queries)
  - You change the guidelines corpus (different documents to match)

Run with: PYTHONPATH=. python3 build/precompute_embeddings.py
"""

import json
from pathlib import Path

import numpy as np
import joblib
import chromadb
from chromadb.utils import embedding_functions

from data.generator import load_dataset
from models.explainer import RiskExplainer
from agents.literature_retriever import _features_to_tags, CHROMA_PATH, COLLECTION_NAME


OUTPUT_PATH = "data/retriever_cache.json"


def collect_query_space() -> set[str]:
    """Run every patient through the retriever's tag logic, collect queries."""
    print("Loading dataset and models...")
    patients = load_dataset("synthetic_data.json")
    explainer = RiskExplainer()

    queries = set()
    print(f"Enumerating queries from {len(patients)} patients...")
    for i, patient in enumerate(patients):
        if i % 500 == 0:
            print(f"  {i}/{len(patients)} processed; {len(queries)} unique queries so far")
        explanation = explainer.explain(patient)
        significant = [c for c in explanation["top_contributions"]
                       if abs(c["shap_value"]) > 0.01]
        tags = _features_to_tags(significant)
        if tags:
            queries.add(" ".join(tags))

    # Add the empty-tag fallback as a sentinel
    queries.add("")
    print(f"  Final query space size: {len(queries)} distinct queries")
    return queries


def precompute_cache(queries: set[str]) -> dict:
    """For each query, retrieve top-3 guidelines from ChromaDB and store."""
    print("\nConnecting to ChromaDB to materialize results...")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2"
    )
    collection = client.get_collection(name=COLLECTION_NAME, embedding_function=embed_fn)

    cache = {}
    print(f"Materializing top-3 results for {len(queries)} queries...")
    for i, query in enumerate(sorted(queries)):
        if not query:
            # Empty-query fallback: return nothing rather than an arbitrary match
            cache[query] = {"guidelines": [], "sources": []}
            continue

        results = collection.query(query_texts=[query], n_results=3)
        guidelines = []
        sources = []
        if results["documents"] and results["documents"][0]:
            for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
                guidelines.append({
                    "summary": doc,
                    "source": meta["source"],
                    "issuing_body": meta["issuing_body"],
                })
                if meta["source"] not in sources:
                    sources.append(meta["source"])
        cache[query] = {"guidelines": guidelines, "sources": sources}

    return cache


def save_cache(cache: dict, path: str = OUTPUT_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(cache, f, indent=2)
    size_kb = Path(path).stat().st_size / 1024
    print(f"\n Cache saved to {path} ({size_kb:.1f} KB, {len(cache)} entries)")


if __name__ == "__main__":
    queries = collect_query_space()
    cache = precompute_cache(queries)
    save_cache(cache)
    print("\nThe runtime retriever can now load this JSON and skip the embedder + ChromaDB entirely.")