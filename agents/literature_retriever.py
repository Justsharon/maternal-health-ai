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


def _get_collection():
    """Load the ChromaDB guidelines collection (once)."""
    global _collection
    if _collection is None:
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
    # Deduplicate while preserving order
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
    
    Reads:  explanation (top_contributions)
    Writes: relevant_guidelines, guideline_sources
    """
    explanation = state.get("explanation") or {}
    top_contributions = explanation.get("top_contributions", [])
    
    # Only consider features that actually moved the estimate
    significant = [c for c in top_contributions if abs(c["shap_value"]) > 0.01]
    
    tags = _features_to_tags(significant)
    
    if not tags:
        state["relevant_guidelines"] = []
        state["guideline_sources"] = []
        return state
    
    collection = _get_collection()
    
    # Build a query from the tags (the trust boundary: we query for the
    # clinical domains the patient's risk factors fall into)
    query_text = " ".join(tags)
    
    results = collection.query(
        query_texts=[query_text],
        n_results=top_n,
    )
    
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
    
    return state


def format_guidance_for_display(state: SentinelState) -> str:
    """
    Format the retrieved guidance with the anti-validation framing.
    This is what the dashboard will show — clearly separated from the
    prediction, framed as 'related' not 'supporting'.
    """
    guidelines = state.get("relevant_guidelines") or []
    if not guidelines:
        return "No directly related guidance found for this patient's risk factors."
    
    lines = ["Related clinical guidance (for the risk factors in this assessment):"]
    lines.append("")
    for g in guidelines:
        lines.append(f"• {g['source']}")
        lines.append(f"  {g['summary']}")
        lines.append("")
    lines.append(
        "Note: This guidance relates to the clinical factors considered in "
        "this assessment. It does not validate or endorse the model's specific "
        "risk estimate. Clinical judgment and confirmation are required."
    )
    return "\n".join(lines)


# --- Standalone test ---
if __name__ == "__main__":
    from data.generator import load_dataset
    from models.explainer import RiskExplainer
    
    patients = load_dataset("synthetic_data.json")
    explainer = RiskExplainer()
    
    # Find a high-risk patient (BP-driven) and test retrieval
    high_risk = None
    for p in patients:
        exp = explainer.explain(p)
        if exp["probability"] > 0.6:
            high_risk = (p, exp)
            break
    
    if high_risk:
        patient, exp = high_risk
        state = {
            "explanation": {
                "top_contributions": exp["top_contributions"],
            }
        }
        result = literature_retriever(state)
        
        print("=" * 65)
        print(f"PATIENT: {patient.patient_id} (week {patient.current_gestational_week})")
        print("=" * 65)
        print("\nTop risk-driving features:")
        for c in exp["top_contributions"][:5]:
            if abs(c["shap_value"]) > 0.01:
                print(f"  {c['feature']}: {c['shap_value']:+.3f}")
        
        tags = _features_to_tags(
            [c for c in exp["top_contributions"] if abs(c["shap_value"]) > 0.01]
        )
        print(f"\nMapped topic tags: {tags}")
        
        print(f"\nRetrieved {len(result['relevant_guidelines'])} guidelines")
        print(f"Sources: {result['guideline_sources']}")
        print()
        print("-" * 65)
        print(format_guidance_for_display(result))