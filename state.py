"""
Sentinel — Shared State Definition

The state flows through all nine agents. Each agent reads specific fields
and writes its own outputs. This is the contract that holds the system together.

Reference: LangGraph stateful workflows (Phase 3 patterns applied to healthcare).
"""

from typing import TypedDict, Optional


class SentinelState(TypedDict):
    """
    Shared state carried through Sentinel's agent pipeline.
    
    Each agent's outputs are documented by which agent owns them.
    """
    
    # --- Input (provided at invocation) ---
    raw_patient_data: dict          # unvalidated incoming record
    
    # --- Set by Privacy Gate (Agent 1) ---
    validated_record: Optional[dict]    # schema-validated, minimised record
    privacy_passed: Optional[bool]      # did the record pass the privacy gate
    privacy_notes: Optional[str]        # what happened (logged)
    fields_stripped: Optional[list]     # which fields were removed (audit)
    
    # --- Set by Risk Predictor (Agent 2) ---
    risk_probability: Optional[float]
    
    # --- Set by Confidence Calibrator (Agent 3) ---
    confidence: Optional[float]
    reliability_flag: Optional[str]     # "reliable" | "reduced_reliability"
    reliability_reason: Optional[str]
    
    # --- Set by Router (Agent 4) ---
    routing_decision: Optional[str]     # "in_scope" | "escalate" | "out_of_scope"
    
    # --- Set by Risk Explainer (Agent 5) ---
    explanation: Optional[dict]         # SHAP-based feature contributions
    
    # --- Set by Literature Retriever (Agent 6) ---
    relevant_guidelines: Optional[list]
    guideline_sources: Optional[list]
    
    # --- Set by Fairness Auditor (Agent 7) ---
    fairness_metadata: Optional[dict]   # demographic info logged for batch audit
    
    # --- Set by Clinical Reviewer (Agent 8) ---
    review_status: Optional[str]        # "approved" | "needs_review" | "escalate"
    review_notes: Optional[str]
    final_recommendation: Optional[str]
    
    # --- Set by Audit Logger (Agent 9) ---
    audit_logged: Optional[bool]
    audit_id: Optional[str]
    
    # --- Clinician decision (set after dashboard interaction) ---
    clinician_decision: Optional[str]   # "confirmed" | "modified" | "rejected"