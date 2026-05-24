"""
Sentinel — Risk Explainer (Agent 5)

Converts SHAP feature contributions into clinician-readable narrative,
grounded STRICTLY in the actual SHAP values. The LLM may rephrase and
organise — it may NOT invent clinical mechanisms or causes.

Guardrail: the prompt provides only the SHAP data and explicitly forbids
adding causal claims. The Clinical Reviewer (Agent 8) later verifies
faithfulness via a Generator-Critic pass.

Reference: Aria's grounded drafter pattern (only use retrieved content),
applied to "only use actual SHAP values".
"""

from state import SentinelState
from agents.llm_helper import call_llm
from models.explainer import RiskExplainer
from data.schema import PatientRecord


# Shared explainer instance (loads models once)
_explainer = None


EXPLAINER_SYSTEM_PROMPT = """You are a clinical decision-support assistant that explains \
risk model outputs to obstetric clinicians. You describe what a risk model's feature \
contributions show — nothing more.

STRICT RULES:
1. Describe ONLY the feature contributions provided. Do NOT invent clinical mechanisms, \
causes, or pathophysiology that are not in the data.
2. Do NOT recite the raw numeric contribution values (e.g. "+0.420"). These are not \
clinically meaningful to a reader. Instead describe direction (increased/decreased the \
estimate) and relative importance (the largest contributor, a smaller contributor, etc.).
3. Do NOT claim a feature "causes" pre-eclampsia. Say it "contributed to" or "increased/\
decreased the model's estimate".
4. Always anchor the estimate to the population baseline provided.
5. Always end with: clinical correlation and clinician confirmation are required.
6. Use clear, professional language an OBGYN would respect. No hype, no false certainty.
7. Keep it under 120 words.

You are describing a model's reasoning, not making a diagnosis."""

def _format_shap_for_prompt(explanation: dict) -> str:
    """Format SHAP output into a clean prompt input."""
    lines = [
        f"Risk estimate: {explanation['probability']:.1%}",
        f"Population baseline: {explanation['base_probability']:.1%}",
        "",
        "Feature contributions (SHAP values — positive increases the estimate, "
        "negative decreases it):",
    ]
    for c in explanation["top_contributions"]:
        if abs(c["shap_value"]) > 0.01:
            direction = "increased" if c["shap_value"] > 0 else "decreased"
            lines.append(f"  - {c['label']}: {direction} the estimate "
                         f"(contribution {c['shap_value']:+.3f})")
    return "\n".join(lines)


def risk_explainer(state: SentinelState) -> SentinelState:
    """
    Agent 5 — generate a grounded plain-language explanation.
    
    Reads:  validated_record
    Writes: explanation (dict with both raw SHAP and the narrative)
    """
    global _explainer
    if _explainer is None:
        _explainer = RiskExplainer()
    
    record = PatientRecord(**state["validated_record"])
    
    # Get SHAP explanation (deterministic, from Day 4)
    shap_explanation = _explainer.explain(record)
    
    # Build grounded prompt
    user_prompt = _format_shap_for_prompt(shap_explanation)
    
    # Generate narrative (LLM rephrases, doesn't invent)
    narrative = call_llm(
        system_prompt=EXPLAINER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.2,
    )
    
    # Store BOTH the raw SHAP (provable) and the narrative (readable)
    state["explanation"] = {
        "probability": shap_explanation["probability"],
        "base_probability": shap_explanation["base_probability"],
        "top_contributions": shap_explanation["top_contributions"],
        "narrative": narrative,
    }
    
    return state


# --- Standalone test ---
if __name__ == "__main__":
    import os
    from data.generator import load_dataset
    
    # For testing without an API key, you can set RECORD_LLM=true with a key,
    # or USE_MOCK_LLM=true after recordings exist.
    print(f"Mock mode: {os.getenv('USE_MOCK_LLM', 'false')}")
    print(f"Record mode: {os.getenv('RECORD_LLM', 'false')}")
    print()
    
    patients = load_dataset("synthetic_data.json")
    _explainer = RiskExplainer()
    
    # Find a high-risk patient
    high_risk = None
    for p in patients:
        exp = _explainer.explain(p)
        if exp["probability"] > 0.6:
            high_risk = p
            break
    
    if high_risk:
        state = {"validated_record": high_risk.model_dump(mode="json")}
        result = risk_explainer(state)
        
        print("=" * 65)
        print(f"PATIENT: {high_risk.patient_id}")
        print(f"  Week {high_risk.current_gestational_week}, "
              f"Age {high_risk.age}, BMI {high_risk.bmi_at_booking}")
        print("=" * 65)
        print(f"\nRisk: {result['explanation']['probability']:.1%}")
        print(f"Baseline: {result['explanation']['base_probability']:.1%}")
        print("\nTop SHAP contributions (the ground truth):")
        for c in result['explanation']['top_contributions'][:5]:
            if abs(c['shap_value']) > 0.01:
                print(f"  {c['label']}: {c['shap_value']:+.3f}")
        print(f"\nLLM Narrative (must be grounded in above):")
        print(f"  {result['explanation']['narrative']}")