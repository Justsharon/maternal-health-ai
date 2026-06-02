"""
Sentinel — Clinical Reviewer (Agent 8)

Generator-Critic pattern. Reviews the risk explanation for FAITHFULNESS
to the SHAP ground truth — the primary failure being fabricated causation
(a fluent, confident clinical claim not supported by the feature
contributions).

The reviewer is grounded in the SAME source of truth as the explainer
(the SHAP values), which is what makes faithfulness checking possible. A
critic that only saw the narrative could judge tone but not faithfulness.

Review hierarchy:
  1. Fabricated causation (primary) — claims not traceable to SHAP
  2. Overconfidence — certainty the prediction doesn't warrant
  3. Missing reliability caveat — dropped the reduced-reliability flag
  4. Tone/ambiguity (secondary)

Reference: Aria Generator-Critic (different persona, fresh evaluation,
breaks correlated failure); the Day-3 fabrication risk this was built for.
"""

import json
from state import SentinelState
from agents.llm_helper import call_llm


REVIEWER_SYSTEM_PROMPT = """You are a clinical safety reviewer auditing an AI-generated \
explanation of a maternal-health risk prediction. Your ONLY job is to verify the \
explanation is faithful to the model's actual feature contributions (provided as ground \
truth). You are a strict critic, not a helper.

NOTE: The narrative may begin with a system-generated reliability notice (e.g. starting \
with "⚠️ Reduced reliability..."). This is appended deterministically by code, NOT by the \
explainer LLM. DO NOT review the reliability notice — focus only on the contribution \
prose that follows it.

You will receive:
1. GROUND TRUTH: the model's actual SHAP feature contributions.
2. NARRATIVE: the explanation generated for a clinician (which may include a system
   reliability notice followed by the contribution prose).

Check the CONTRIBUTION PROSE for these violations, in priority order:
1. FABRICATED CAUSATION: Does it claim any clinical mechanism, cause, or pathophysiology \
NOT present in the ground-truth contributions? (e.g. inventing "placental insufficiency" \
when SHAP only listed "rising BP".) This is the most serious violation.
2. UNSUPPORTED FEATURE: Does it reference any factor not in the ground truth?
3. OVERCONFIDENCE: Does it state certainty the probabilistic estimate doesn't warrant?

Approve if the contribution prose meets ALL these conditions:
  - Every clinical claim traces to a feature in the ground truth.
  - No invented causation, mechanism, or pathophysiology.
  - No overstated certainty.

Stylistic preferences (tone, phrasing, "could be clearer") are NOT violations. A \
narrative that is grounded but plain should be approved.

When in doubt about whether something is a real violation versus a style preference, \
approve and note the concern in the notes field. A false flag trains clinicians to \
ignore the reviewer; only flag when there is a real, nameable violation.

Respond ONLY with valid JSON, no preamble:
{
  "approved": true or false,
  "violations": ["specific description of each violation found, empty if none"],
  "notes": "one-sentence summary"
}"""


def _build_review_prompt(state: SentinelState) -> str:
    explanation = state.get("explanation") or {}
    contributions = explanation.get("top_contributions", [])
    narrative = explanation.get("narrative", "")
    reliability = state.get("reliability_flag", "unknown")

    ground_truth_lines = ["GROUND TRUTH — model feature contributions:"]
    for c in contributions:
        if abs(c["shap_value"]) > 0.01:
            direction = "increased" if c["shap_value"] > 0 else "decreased"
            ground_truth_lines.append(
                f"  - {c['label']}: {direction} the estimate"
            )

    return (
        "\n".join(ground_truth_lines)
        + f"\n\nRELIABILITY: {reliability}"
        + f"\n\nNARRATIVE TO REVIEW:\n{narrative}"
    )


def clinical_reviewer(state: SentinelState) -> SentinelState:
    """
    Agent 8 — review the explanation for faithfulness to SHAP ground truth.

    Reads:  explanation, reliability_flag
    Writes: review_status, review_notes
    """
    # If there's no explanation (e.g. out_of_scope path), nothing to review
    if not state.get("explanation"):
        state["review_status"] = "no_explanation"
        state["review_notes"] = "No explanation generated; nothing to review."
        return state

    user_prompt = _build_review_prompt(state)
    raw = call_llm(
        system_prompt=REVIEWER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.0,   # deterministic, strict
    )

    # Parse the JSON verdict defensively
    try:
        cleaned = raw.strip().replace("```json", "").replace("```", "").strip()
        verdict = json.loads(cleaned)
        approved = bool(verdict.get("approved", False))
        violations = verdict.get("violations", [])
        notes = verdict.get("notes", "")
    except (json.JSONDecodeError, AttributeError):
        # If the reviewer's output can't be parsed, FAIL SAFE: flag for review
        approved = False
        violations = ["Reviewer output could not be parsed — failing safe."]
        notes = "Unparseable reviewer response; flagged for human review."

    state["review_status"] = "approved" if approved else "needs_review"
    state["review_notes"] = (
        notes if approved
        else f"{notes} Violations: {'; '.join(violations)}"
    )
    return state


# --- Standalone test ---
if __name__ == "__main__":
    import os
    os.environ["USE_MOCK_LLM"] = "false"  # need live review for the test
    # (record these test cases once with RECORD_LLM=true + GROQ_API_KEY)

    # Test A — a FAITHFUL narrative (should approve)
    faithful_state = {
        "reliability_flag": "reliable",
        "explanation": {
            "top_contributions": [
                {"label": "rising BP trajectory", "shap_value": 0.42},
                {"label": "systolic BP range", "shap_value": 0.27},
                {"label": "current gestational age", "shap_value": -0.14},
            ],
            "narrative": (
                "The estimate is increased above baseline, driven mainly by a "
                "rising blood pressure trajectory and variation in systolic "
                "readings. Current gestational age slightly lowered the estimate. "
                "Clinical correlation and confirmation are required."
            ),
        },
    }

    # Test B — a FABRICATED narrative (should flag)
    fabricated_state = {
        "reliability_flag": "reliable",
        "explanation": {
            "top_contributions": [
                {"label": "rising BP trajectory", "shap_value": 0.42},
            ],
            "narrative": (
                "The rising blood pressure indicates developing placental "
                "insufficiency and endothelial dysfunction, which are the "
                "underlying causes of pre-eclampsia in this patient. Immediate "
                "delivery is certainly indicated."
            ),
        },
    }

    print("TEST A — Faithful narrative (expect APPROVED):")
    result = clinical_reviewer(faithful_state)
    print(f"  Status: {result['review_status']}")
    print(f"  Notes:  {result['review_notes']}")
    print()

    print("TEST B — Fabricated narrative (expect NEEDS_REVIEW):")
    result = clinical_reviewer(fabricated_state)
    print(f"  Status: {result['review_status']}")
    print(f"  Notes:  {result['review_notes']}")