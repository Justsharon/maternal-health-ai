"""
Sentinel — Router (Agent 4)

Two-signal escalation logic:
  1. Reliability flag  — healthcare-specific; escalate when model operates
                         outside its validated range, regardless of confidence
  2. Confidence score  — Aria-style; escalate when prediction is in the
                         uncertain middle

Decision: in_scope | escalate | out_of_scope

Reference: confidence-first routing (Aria/Phase 3), extended with the
reliability dimension specific to clinical models operating across regimes.
"""

from state import SentinelState


# Below this confidence, escalate even if reliability is fine
CONFIDENCE_ESCALATION_THRESHOLD = 0.3


def router(state: SentinelState) -> SentinelState:
    """
    Agent 4 — decide how the prediction is handled.
    
    Reads:  privacy_passed, risk_probability, confidence, reliability_flag
    Writes: routing_decision
    """
    privacy_passed = state.get("privacy_passed")
    confidence = state.get("confidence")
    reliability_flag = state.get("reliability_flag")
    
    # --- Check 1: Privacy gate must have passed ---
    # Defensive: this should never be reached if privacy failed, but we
    # never let an unvalidated record proceed.
    if not privacy_passed:
        state["routing_decision"] = "out_of_scope"
        return state
    
    # --- Check 2: Reliability flag (healthcare-specific trigger) ---
    # A reduced-reliability prediction escalates REGARDLESS of confidence.
    # This is the week-13-patient case: a confident-looking 4% that the
    # model cannot be trusted on because BP trajectory signal is absent.
    if reliability_flag == "reduced_reliability":
        state["routing_decision"] = "escalate"
        return state
    
    # --- Check 3: Confidence threshold (Aria-style trigger) ---
    # Prediction sits in the uncertain middle — escalate to a specialist.
    if confidence is None or confidence < CONFIDENCE_ESCALATION_THRESHOLD:
        state["routing_decision"] = "escalate"
        return state
    
    # --- Otherwise: proceed ---
    state["routing_decision"] = "in_scope"
    return state


# --- Standalone test ---
if __name__ == "__main__":
    
    def make_state(privacy_passed, confidence, reliability_flag):
        return {
            "privacy_passed": privacy_passed,
            "risk_probability": 0.5,
            "confidence": confidence,
            "reliability_flag": reliability_flag,
        }
    
    test_cases = [
        # (description, state, expected_decision)
        (
            "Reliable, high confidence → in_scope",
            make_state(True, 0.85, "reliable"),
            "in_scope",
        ),
        (
            "Reliable, low confidence → escalate",
            make_state(True, 0.15, "reliable"),
            "escalate",
        ),
        (
            "Reduced reliability, HIGH confidence → escalate (healthcare trigger)",
            make_state(True, 0.92, "reduced_reliability"),
            "escalate",
        ),
        (
            "Reduced reliability, low confidence → escalate",
            make_state(True, 0.10, "reduced_reliability"),
            "escalate",
        ),
        (
            "Privacy failed → out_of_scope",
            make_state(False, 0.85, "reliable"),
            "out_of_scope",
        ),
        (
            "Confidence exactly at threshold (0.3) → in_scope",
            make_state(True, 0.30, "reliable"),
            "in_scope",
        ),
        (
            "Confidence just below threshold → escalate",
            make_state(True, 0.29, "reliable"),
            "escalate",
        ),
    ]
    
    print("Router decision tests:\n")
    all_passed = True
    for description, state, expected in test_cases:
        result = router(state)
        decision = result["routing_decision"]
        status = "✅" if decision == expected else "❌"
        if decision != expected:
            all_passed = False
        print(f"{status} {description}")
        print(f"    Expected: {expected:15s} Got: {decision}")
        print()
    
    print("=" * 60)
    if all_passed:
        print("✅ All router tests passed.")
    else:
        print("❌ Some tests failed — review the logic.")