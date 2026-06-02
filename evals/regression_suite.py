"""
Sentinel — Regression Test Suite

Single-command verification that every safety property of Sentinel still
holds. Runs against:
  - The gold set (100 held-out patients) for model performance
  - The full synthetic dataset for fairness aggregate metrics
  - Synthetic invalid records for schema integrity
  - The orchestrator's three routing paths for pipeline integrity
  - Pre-recorded fabrication test cases for reviewer faithfulness

Design principle: the gold set proxies for external validity (the Wong
sepsis lesson). High training-data performance is a statistical artifact;
high gold-set performance is evidence of generalization.

Run all:           pytest evals/regression_suite.py
Run one:           pytest evals/regression_suite.py::test_recall_holds
Run with output:   pytest -v evals/regression_suite.py
"""

import os
import json
import numpy as np
import joblib
import pytest
from pydantic import ValidationError

# Force deterministic mock mode for ALL tests — never burn API calls in CI
os.environ["USE_MOCK_LLM"] = "true"

from data.schema import PatientRecord
from data.generator import load_dataset
from models.feature_extractor import build_feature_matrix
from orchestrator import assess_patient
from agents.fairness_auditor import audit_fairness, RESIDUAL_GROUPS
from agents.clinical_reviewer import clinical_reviewer


# --- Acceptance thresholds (the decision lines documented in operating_point.md) ---

OPERATING_THRESHOLD = 0.1
MIN_GOLD_SET_RECALL = 0.80     # at threshold 0.1, per operating_point.md
MAX_NAMED_GROUP_EO_GAP = 0.10  # equalized odds diff among named clinical groups


# --- 1. Schema integrity ---

def test_schema_strips_unauthorized_fields():
    """Privacy gate: extra fields must be stripped, not propagated."""
    record_with_phi = {
        "patient_id": "SYN-TEST", "is_synthetic": True, "age": 30,
        "ethnicity": "white", "socioeconomic_proxy": "middle",
        "parity": 1, "current_gestational_week": 24, "bmi_at_booking": 25.0,
        "patient_name": "Jane Doe",        # unauthorized
        "national_id": "12345",            # unauthorized PHI
    }
    record = PatientRecord(**record_with_phi)
    dumped = record.model_dump()
    assert "patient_name" not in dumped, "PHI field leaked through schema"
    assert "national_id" not in dumped, "PHI field leaked through schema"


def test_schema_rejects_non_synthetic():
    """Synthetic-only enforcement: real-data records must be refused."""
    record = {
        "patient_id": "REAL-TEST", "is_synthetic": False, "age": 30,
        "ethnicity": "white", "socioeconomic_proxy": "middle",
        "parity": 1, "current_gestational_week": 24, "bmi_at_booking": 25.0,
    }
    with pytest.raises(ValidationError):
        PatientRecord(**record)


# --- 2. Model performance on the gold set ---

def test_recall_holds_on_gold_set():
    """At operating threshold 0.1, recall on the gold set must hold."""
    with open("evals/gold_set.json") as f:
        gold = json.load(f)
    model = joblib.load("models/risk_model.joblib")
    
    X = np.array([c["features"] for c in gold], dtype=np.float32)
    y_true = np.array([c["true_outcome"] for c in gold])
    y_proba = model.predict_proba(X)[:, 1]
    y_pred = (y_proba >= OPERATING_THRESHOLD).astype(int)
    
    recall = (y_pred[y_true == 1].sum() / y_true.sum())
    assert recall >= MIN_GOLD_SET_RECALL, (
        f"Recall {recall:.3f} fell below threshold {MIN_GOLD_SET_RECALL}. "
        f"A model change has degraded performance on held-out edge cases."
    )


# --- 3. Fairness ---

def test_equalized_odds_among_named_groups():
    """Named clinical groups must have equalized-odds gap below threshold.
    
    Residual buckets ('other', 'not_disclosed') are excluded — they are
    heterogeneous and may show artifactual disparities (the Day-1 insight).
    """
    report = audit_fairness(
        protected_attribute="ethnicity",
        threshold=OPERATING_THRESHOLD,
    )
    
    named_tprs = {
        g: v for g, v in report.per_group_tpr.items()
        if g not in RESIDUAL_GROUPS
    }
    named_gap = max(named_tprs.values()) - min(named_tprs.values())
    
    assert named_gap < MAX_NAMED_GROUP_EO_GAP, (
        f"Recall gap among named clinical groups {named_gap:.3f} exceeds "
        f"{MAX_NAMED_GROUP_EO_GAP}. Per-group recalls: {named_tprs}"
    )


# --- 4. Pipeline routing ---

@pytest.fixture(scope="module")
def patients():
    return load_dataset("synthetic_data.json")


def test_in_scope_route_completes(patients):
    """A reliable, late-pregnancy patient should route in_scope and produce
    a complete assessment with all expected state fields populated."""
    patient = next(
        p for p in patients
        if p.current_gestational_week >= 28
        and len(p.blood_pressure_readings) >= 4
    )
    result = assess_patient(patient.model_dump(mode="json"))
    
    assert result["privacy_passed"] is True
    assert result["risk_probability"] is not None
    assert result["routing_decision"] in ("in_scope", "escalate")
    assert result["audit_logged"] is True
    assert result["audit_id"] is not None


def test_escalate_route_on_early_pregnancy(patients):
    """An early-pregnancy patient must trigger reduced reliability AND escalate."""
    patient = next(p for p in patients if p.current_gestational_week <= 15)
    result = assess_patient(patient.model_dump(mode="json"))
    
    assert result["reliability_flag"] == "reduced_reliability"
    assert result["routing_decision"] == "escalate"
    assert result["audit_logged"] is True


def test_privacy_failure_short_circuits(patients):
    """A non-synthetic record must terminate at the privacy gate.
    Prediction must NOT happen. Audit must still log the rejection."""
    bad = patients[0].model_dump(mode="json")
    bad["is_synthetic"] = False
    
    result = assess_patient(bad)
    
    assert result["privacy_passed"] is False
    # Use .get() because these fields are intentionally absent on the
    # rejected path — the pipeline correctly never reached the nodes that
    # would have set them. KeyError would be the wrong failure mode here.
    assert result.get("risk_probability") is None    # never predicted
    assert result.get("routing_decision") is None    # never routed
    assert result["audit_logged"] is True            # but still logged


# --- 5. Reviewer faithfulness ---

def test_reviewer_approves_faithful_narrative(monkeypatch):
    """A narrative that matches the SHAP ground truth must be approved."""
    # Stub the LLM call with a deterministic faithful verdict.
    # We're testing the REVIEWER AGENT (parsing, state-writing, fail-safe
    # behavior), not whether Groq specifically returns approved. That's
    # what the standalone clinical_reviewer.py tests cover.
    import agents.clinical_reviewer as cr
    monkeypatch.setattr(cr, "call_llm", lambda **kwargs: json.dumps({
        "approved": True,
        "violations": [],
        "notes": "Narrative is grounded in ground truth.",
    }))
    
    state = {
        "reliability_flag": "reliable",
        "explanation": {
            "top_contributions": [
                {"label": "rising BP trajectory", "shap_value": 0.42},
            ],
            "narrative": "Grounded narrative.",
        },
    }
    result = clinical_reviewer(state)
    assert result["review_status"] == "approved"


def test_reviewer_catches_fabricated_causation(monkeypatch):
    """A narrative inventing clinical mechanisms must be flagged."""
    import agents.clinical_reviewer as cr
    monkeypatch.setattr(cr, "call_llm", lambda **kwargs: json.dumps({
        "approved": False,
        "violations": ["FABRICATED CAUSATION: invented placental insufficiency"],
        "notes": "Narrative invents mechanism not in ground truth.",
    }))
    
    state = {
        "reliability_flag": "reliable",
        "explanation": {
            "top_contributions": [
                {"label": "rising BP trajectory", "shap_value": 0.42},
            ],
            "narrative": "Fabricated narrative.",
        },
    }
    result = clinical_reviewer(state)
    assert result["review_status"] == "needs_review"