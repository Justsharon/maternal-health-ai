"""
Sentinel — Privacy Gate (Agent 1)

The first node in the pipeline. Enforces:
  1. Schema validation (rejects malformed / non-synthetic records)
  2. Data minimisation (only schema fields proceed)
  3. Access logging (records what data was processed)

Reference: WHO Principle 6 (privacy by design), HIPAA minimum-necessary.
"""

from pydantic import ValidationError
from data.schema import PatientRecord
from state import SentinelState


def privacy_gate(state: SentinelState) -> SentinelState:
    """
    Validate and minimise the incoming patient record.
    
    Reads:  raw_patient_data
    Writes: validated_record, privacy_passed, privacy_notes, fields_stripped
    """
    raw = state["raw_patient_data"]
    
    # Track which fields will be stripped (present in raw but not in schema)
    schema_fields = set(PatientRecord.model_fields.keys())
    incoming_fields = set(raw.keys())
    stripped = list(incoming_fields - schema_fields)
    
    try:
        # Pydantic validates AND strips extra fields (extra="ignore" in schema)
        validated = PatientRecord(**raw)
        
        state["validated_record"] = validated.model_dump(mode="json")
        state["privacy_passed"] = True
        state["fields_stripped"] = stripped
        
        if stripped:
            state["privacy_notes"] = (
                f"Record validated. Stripped {len(stripped)} unauthorised "
                f"field(s): {', '.join(stripped)}"
            )
        else:
            state["privacy_notes"] = "Record validated. No unauthorised fields present."
    
    except ValidationError as e:
        # Record failed validation — DO NOT let it proceed
        state["validated_record"] = None
        state["privacy_passed"] = False
        state["fields_stripped"] = []
        
        # Summarise the validation errors without exposing raw data
        error_summary = "; ".join([
            f"{err['loc'][0] if err['loc'] else 'record'}: {err['msg']}"
            for err in e.errors()
        ])
        state["privacy_notes"] = f"Record rejected at privacy gate: {error_summary}"
    
    return state


# --- Standalone test ---
if __name__ == "__main__":
    # Test 1 — valid record passes
    valid_record = {
        "patient_id": "SYN-TEST-1",
        "is_synthetic": True,
        "age": 32,
        "ethnicity": "black_african",
        "socioeconomic_proxy": "middle",
        "parity": 1,
        "multiple_pregnancy": False,
        "current_gestational_week": 24,
        "pre_existing_hypertension": False,
        "diabetes": "none",
        "prior_preeclampsia": False,
        "family_history_preeclampsia": True,
        "bmi_at_booking": 28.5,
        "blood_pressure_readings": [
            {"gestational_week": 12, "systolic": 118, "diastolic": 75},
        ],
        "proteinuria_level": 15.0,
        "current_symptoms": {"headache": True},
    }
    
    state = {"raw_patient_data": valid_record}
    result = privacy_gate(state)
    print("Test 1 — Valid record:")
    print(f"  Passed: {result['privacy_passed']}")
    print(f"  Notes: {result['privacy_notes']}")
    print()
    
    # Test 2 — record with unauthorised fields (PHI leak attempt)
    record_with_phi = {
        **valid_record,
        "patient_name": "Jane Doe",        # unauthorised
        "national_id": "12345678",         # unauthorised PHI
        "home_address": "123 Main St",     # unauthorised PHI
    }
    
    state = {"raw_patient_data": record_with_phi}
    result = privacy_gate(state)
    print("Test 2 — Record with unauthorised PHI fields:")
    print(f"  Passed: {result['privacy_passed']}")
    print(f"  Stripped: {result['fields_stripped']}")
    print(f"  Notes: {result['privacy_notes']}")
    # Verify PHI didn't make it into validated record
    assert "patient_name" not in result["validated_record"]
    assert "national_id" not in result["validated_record"]
    print("PHI fields confirmed stripped from validated record")
    print()
    
    # Test 3 — non-synthetic record rejected
    non_synthetic = {**valid_record, "is_synthetic": False}
    state = {"raw_patient_data": non_synthetic}
    result = privacy_gate(state)
    print("Test 3 — Non-synthetic record:")
    print(f"  Passed: {result['privacy_passed']}")
    print(f"  Notes: {result['privacy_notes']}")
    assert result["privacy_passed"] is False
    print("Non-synthetic record correctly rejected")
    print()
    
    # Test 4 — malformed record rejected
    malformed = {**valid_record, "age": 200}  # impossible age
    state = {"raw_patient_data": malformed}
    result = privacy_gate(state)
    print("Test 4 — Malformed record (age 200):")
    print(f"  Passed: {result['privacy_passed']}")
    print(f"  Notes: {result['privacy_notes']}")
    assert result["privacy_passed"] is False
    print("Malformed record correctly rejected")