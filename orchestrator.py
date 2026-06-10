"""
Sentinel — Orchestrator

Wires the agent pipeline into a LangGraph StateGraph with conditional
routing. Acyclic by design: every path terminates at END. recursion_limit
is the seatbelt; the acyclic graph is driving safely.

ARCHITECTURE (run-but-reframe):
  privacy_gate -> [privacy check] -> risk_predictor -> confidence_calibrator
    -> router -> {
        in_scope  -> explainer -> retriever -> audit -> END
        escalate  -> explainer -> retriever -> audit -> END  (reframed)
        out_of_scope -> audit -> END  (skip explain/retrieve — no valid patient)
      }

COST DESIGN (load-once): all heavy objects (models, ChromaDB, OOD stats)
are module-level singletons inside their agents — loaded once at first
call, reused across all requests. Per-request cost is O(1) inference +
at most one LLM call, not O(N) dataset loading.

DEMO-GRADE: synchronous, single-process, in-memory. Production changes
noted at end of build.
"""

from langgraph.graph import StateGraph, END

from state import SentinelState
from agents.privacy_gate import privacy_gate
from agents.risk_predictor import risk_predictor
from agents.confidence_calibrator import confidence_calibrator
from agents.router import router
from agents.risk_explainer import risk_explainer
from agents.literature_retriever import literature_retriever
from agents.clinical_reviewer import clinical_reviewer 
from agents.audit_logger import audit_logger


# --- Conditional edge functions ---

def after_privacy(state: SentinelState) -> str:
    """If privacy failed, skip straight to out_of_scope handling."""
    if not state.get("privacy_passed"):
        return "rejected"
    return "proceed"


def after_router(state: SentinelState) -> str:
    """
    Route based on the router's decision.
    in_scope + escalate both go to the explainer (run-but-reframe).
    out_of_scope skips to audit.
    """
    decision = state.get("routing_decision")
    if decision == "out_of_scope":
        return "skip_to_audit"
    # both in_scope and escalate run the explainer + retriever
    return "explain"


# --- Build the graph ---

def build_sentinel():
    graph = StateGraph(SentinelState)

    # Register nodes
    graph.add_node("privacy_gate", privacy_gate)
    graph.add_node("risk_predictor", risk_predictor)
    graph.add_node("confidence_calibrator", confidence_calibrator)
    graph.add_node("router", router)
    graph.add_node("risk_explainer", risk_explainer)
    graph.add_node("literature_retriever", literature_retriever)
    graph.add_node("clinical_reviewer", clinical_reviewer)
    graph.add_node("audit_logger", audit_logger)

    # Entry
    graph.set_entry_point("privacy_gate")

    # Privacy gate -> either proceed to prediction, or jump to audit (rejected)
    graph.add_conditional_edges(
        "privacy_gate",
        after_privacy,
        {
            "proceed": "risk_predictor",
            "rejected": "audit_logger",   # rejected records still get logged
        },
    )

    # Linear core: predict -> calibrate -> route
    graph.add_edge("risk_predictor", "confidence_calibrator")
    graph.add_edge("confidence_calibrator", "router")

    # Router -> explain (in_scope/escalate) OR skip to audit (out_of_scope)
    graph.add_conditional_edges(
        "router",
        after_router,
        {
            "explain": "risk_explainer",
            "skip_to_audit": "audit_logger",
        },
    )

    # Explainer -> retriever -> audit -> END
    graph.add_edge("risk_explainer", "literature_retriever")
    graph.add_edge("literature_retriever", "clinical_reviewer")
    graph.add_edge("clinical_reviewer", "audit_logger")
    graph.add_edge("audit_logger", END)

    return graph.compile()


# Module singleton — compile once
_sentinel = None


def get_sentinel():
    global _sentinel
    if _sentinel is None:
        _sentinel = build_sentinel()
    return _sentinel


def assess_patient(raw_patient_data: dict) -> SentinelState:
    """
    Single entry point: take a raw patient record, return the full
    assessment state. This is the API a dashboard or clinic would call.
    """
    app = get_sentinel()
    initial_state = {"raw_patient_data": raw_patient_data}
    # recursion_limit: the seatbelt. The graph is acyclic so this should
    # never trigger — but if a future edit introduces a cycle, this caps it.
    result = app.invoke(initial_state, {"recursion_limit": 15})
    return result


# --- Standalone end-to-end test ---

if __name__ == "__main__":
    import os
    from data.generator import load_dataset

    # Demo-safe: replay recorded LLM responses
    if os.environ.get("RECORD_LLM", "false").lower() != "true":
        os.environ.setdefault("USE_MOCK_LLM", "true")

    patients = load_dataset("synthetic_data.json")

    # Pick three illustrative patients: high-risk reliable, early-pregnancy
    # (escalate), and we'll synthesize a privacy failure.
    high_risk = next(p for p in patients
                     if p.current_gestational_week >= 28
                     and len(p.blood_pressure_readings) >= 4)
    early = next(p for p in patients if p.current_gestational_week <= 15)

    print("=" * 70)
    print("TEST 1 — Standard patient (expect in_scope or escalate)")
    print("=" * 70)
    result = assess_patient(high_risk.model_dump(mode="json"))
    print(f"Patient: {result['validated_record']['patient_id']}")
    print(f"Privacy passed: {result['privacy_passed']}")
    print(f"Risk probability: {result['risk_probability']:.1%}")
    print(f"Confidence: {result['confidence']}")
    print(f"Reliability: {result['reliability_flag']}")
    print(f"Routing decision: {result['routing_decision']}")
    print(
        f"Guidelines found: {len(result.get('relevant_guidelines') or [])}")
    print(f"  Review status:     {result.get('review_status')}")
    print(f"  Review notes:      {(result.get('review_notes') or '')[:100]}")
    print(
        f"Audit logged: {result['audit_logged']} (id: {result['audit_id'][:8]}...)")
    if result.get("explanation"):
        print(
            f"Explanation: {result['explanation']['narrative'][:90]}...")

    print()
    print("=" * 70)
    print("TEST 2 — Early-pregnancy patient (expect escalate, reduced reliability)")
    print("=" * 70)
    result = assess_patient(early.model_dump(mode="json"))
    print(f"Patient: {result['validated_record']['patient_id']} "
          f"(week {result['validated_record']['current_gestational_week']})")
    print(f"Risk probability: {result['risk_probability']:.1%}")
    print(f"Reliability: {result['reliability_flag']}")
    print(f"Routing decision: {result['routing_decision']}")
    print(f"  Review status:     {result.get('review_status')}")     
    print(f"  Review notes:      {(result.get('review_notes') or '')[:100]}") 
    print(f"Audit logged: {result['audit_logged']}")

    print()
    print("=" * 70)
    print("TEST 3 — Privacy failure (non-synthetic record, expect rejection)")
    print("=" * 70)
    bad = high_risk.model_dump(mode="json")
    bad["is_synthetic"] = False
    result = assess_patient(bad)
    print(f"Privacy passed: {result['privacy_passed']}")
    print(f"Privacy notes: {result['privacy_notes'][:80]}...")
    print(f"  Review status:     {result.get('review_status')}")
    print(f"Routing decision: {result.get('routing_decision')}")
    print(f"Risk probability: {result.get('risk_probability')}")
    print(f"Audit logged: {result['audit_logged']}")
