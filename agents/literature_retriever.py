"""
Sentinel — Literature Retriever (Agent 6)

Surfaces attributed clinical guidance related to the FACTORS driving a
patient's risk estimate — never guidance that validates the prediction
itself.

Design principle (anti-validation): the retriever maps the patient's top
SHAP features to topic tags and retrieves guidance about those factors.
The output is framed as "related clinical guidance," with explicit
language that it does not endorse the model's specific estimate.

Reference: Phase 2 RAG; Aria filter-as-trust-boundary; the
unwarranted-validation trap (juxtaposition implies endorsement).
"""

import json
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from state import SentinelState


CHROMA_PATH = "chroma_guidelines"
COLLECTION_NAME = "maternal_health_guidelines"


# Map model feature names → guideline topic tags.
# This is the trust boundary: SHAP features connect to clinical domains
# deterministically, not via fuzzy semantic guessing.
FEATURE_TO_TAGS = {
    "bp_systolic_change": ["bp_trajectory", "blood_pressure", "monitoring"],
    "bp_diastolic_change": ["bp_trajectory", "blood_pressure", "monitoring"],
    "bp_systolic_range": ["blood_pressure", "monitoring"],
    "bp_diastolic_range": ["blood_pressure", "monitoring"],
    "bp_rising_trend": ["bp_trajectory", "blood_pressure", "warning_signs"],
    "bp_max_systolic": ["blood_pressure", "thresholds"],
    "bp_latest_systolic": ["blood_pressure", "thresholds"],
    "prior_preeclampsia": ["risk_factors", "prior_preeclampsia"],
    "pre_existing_hypertension": ["risk_factors", "chronic_hypertension"],
    "is_nulliparous": ["risk_factors", "first_pregnancy"],
    "bmi_at_booking": ["risk_factors", "bmi"],
    "bmi_obese": ["risk_factors", "bmi"],
    "diabetes_any": ["risk_factors"],
    "multiple_pregnancy": ["risk_factors"],
    "proteinuria_level": ["proteinuria", "diagnosis"],
    "any_symptoms": ["symptoms", "warning_signs"],
    "symptom_count": ["symptoms", "warning_signs"],
    "current_gestational_week": ["gestational_age", "timing"],
}


_collection = None
_cache = None


def _load_cache_if_available() -> dict | None:
    """Load the precomputed cache if it exists. Returns None for dev mode."""
    global _cache
    if _cache is not None:
        return _cache
    cache_path = Path("data/retriever_cache.json")
    if not cache_path.exists():
        return None
    with open(cache_path) as f:
        _cache = json.load(f)
    return _cache


def _get_collection():
    """Load the ChromaDB guidelines collection. Used only in dev mode."""
    global _collection
    if _collection is None:
        # Imports kept local so the runtime image doesn't need chromadb +
        # sentence-transformers if the cache exists.
        import chromadb
        from chromadb.utils import embedding_functions
        client = chromadb.PersistentClient(path=CHROMA_PATH)
        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        _collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=embed_fn,
        )
    return _collection


def _features_to_tags(top_contributions: list) -> list:
    """Collect topic tags from the patient's top risk-driving features."""
    tags = []
    for c in top_contributions:
        feature = c["feature"]
        if feature in FEATURE_TO_TAGS:
            tags.extend(FEATURE_TO_TAGS[feature])
    seen = set()
    ordered = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            ordered.append(t)
    return ordered


def literature_retriever(state: SentinelState, top_n: int = 3) -> SentinelState:
    """
    Agent 6 — retrieve guidance related to the patient's risk factors.
    
    Two modes:
      Production: precomputed cache loaded from data/retriever_cache.json
                  (no embedder, no ChromaDB resident in memory)
      Dev:        live ChromaDB query if cache is absent

    Reads:  explanation (top_contributions)
    Writes: relevant_guidelines, guideline_sources
    """
    explanation = state.get("explanation") or {}
    top_contributions = explanation.get("top_contributions", [])
    
    significant = [c for c in top_contributions if abs(c["shap_value"]) > 0.01]
    tags = _features_to_tags(significant)
    
    if not tags:
        state["relevant_guidelines"] = []
        state["guideline_sources"] = []
        return state
    
    query_text = " ".join(tags)
    
    # Try the precomputed cache first (production path)
    cache = _load_cache_if_available()
    if cache is not None:
        cached = cache.get(query_text)
        if cached is not None:
            state["relevant_guidelines"] = cached["guidelines"]
            state["guideline_sources"] = cached["sources"]
            return state
        # Cache exists but this specific query isn't in it — fall through
        # to live retrieval if we have ChromaDB available; otherwise empty.
    
    # Dev mode (or cache miss): live ChromaDB query
    try:
        collection = _get_collection()
        results = collection.query(query_texts=[query_text], n_results=top_n)
        
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
        
        state["relevant_guidelines"] = guidelines
        state["guideline_sources"] = sources
    except Exception:
        # Production with cache miss and no ChromaDB available: return empty
        # rather than crash. Honest fallback.
        state["relevant_guidelines"] = []
        state["guideline_sources"] = []
    
    return state