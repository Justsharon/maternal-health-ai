"""
Sentinel - Risk Predictor (Agent 2)

Single responsibilty: Produce the calibrated risk probability.
Loads the calibrated model ONCE (module singleton) - model loading is a
startup cost, not a per-request cost.

Big-O: O(T) per prediction where T = number of trees (-9). Effectively 0(1).
Memory: one model in memory, shared across all requests.
"""

import joblib
from state import SentinelState
from data.schema import PatientRecord
from models.feature_extractor import extract_features

_model = None  # load-once singleton

def _get_model():
    global _model
    if _model is None:
        _model = joblib.load("models/risk_model.joblib")
    return _model


def risk_predictor(state: SentinelState) -> SentinelState:
    """
    Agent 2 — produce calibrated risk probability.

    Reads:  validated_record
    Writes: risk_probability
    """
    model = _get_model()
    record = PatientRecord(**state["validated_record"])

    x = extract_features(record).reshape(1, -1)
    probability = float(model.predict_proba(x)[0, 1])

    # Cap extremes — clinical credibility (no tool claims certainty)
    probability = min(max(probability, 0.01), 0.95)

    state["risk_probability"] = probability
    return state


if __name__ == "__main__":
    from data.generator import load_dataset
    patients = load_dataset("synthetic_data.json")
    for p in patients[:3]:
        state = {"validated_record": p.model_dump(mode="json")}
        result = risk_predictor(state)
        print(f"{p.patient_id} (week {p.current_gestational_week}): "
              f"risk = {result['risk_probability']:.1%}")