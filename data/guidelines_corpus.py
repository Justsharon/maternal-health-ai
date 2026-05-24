"""
Sentinel — Medical Guidelines Corpus

Conservative, attributed summaries of publicly available maternal health
guidance on hypertension and pre-eclampsia. These are short factual
summaries for demonstration — NOT reproductions of the source documents.

A production system would license full guideline text and link directly
to the issuing bodies (NICE, WHO, ACOG).

Each entry connects to the CLINICAL FACTORS the model uses, so the
retriever surfaces guidance relevant to a patient's risk drivers — not
guidance that "validates" the model's specific numeric prediction.
"""

# Each guideline: id, source attribution, topic tags (matching model
# features), and a short conservative summary in our own words.

GUIDELINES = [
    {
        "id": "nice-ng133-bp-monitoring",
        "source": "NICE Guideline NG133 (Hypertension in pregnancy)",
        "issuing_body": "National Institute for Health and Care Excellence (UK)",
        "topic_tags": ["blood_pressure", "bp_trajectory", "hypertension", "monitoring"],
        "summary": (
            "NICE guidance on hypertension in pregnancy recommends regular "
            "blood pressure monitoring throughout pregnancy, with increased "
            "frequency for those showing rising readings or additional risk "
            "factors. Rising blood pressure trends are a recognised warning "
            "sign warranting closer surveillance."
        ),
    },
    {
        "id": "nice-ng133-risk-factors",
        "source": "NICE Guideline NG133 (Hypertension in pregnancy)",
        "issuing_body": "National Institute for Health and Care Excellence (UK)",
        "topic_tags": ["risk_factors", "prior_preeclampsia", "chronic_hypertension",
                       "first_pregnancy", "bmi"],
        "summary": (
            "Recognised risk factors for pre-eclampsia include prior "
            "pre-eclampsia, chronic hypertension, first pregnancy, raised body "
            "mass index, multiple pregnancy, and pre-existing diabetes. "
            "Presence of high-risk factors may warrant preventive measures and "
            "increased monitoring as determined by the clinician."
        ),
    },
    {
        "id": "who-preeclampsia-prevention",
        "source": "WHO recommendations on prevention and treatment of pre-eclampsia",
        "issuing_body": "World Health Organization",
        "topic_tags": ["prevention", "risk_factors", "calcium", "aspirin"],
        "summary": (
            "WHO recommendations address the prevention and management of "
            "pre-eclampsia, including consideration of preventive measures for "
            "individuals identified as higher risk. Identification of elevated "
            "risk supports timely preventive and monitoring decisions made by "
            "the care team."
        ),
    },
    {
        "id": "acog-bp-thresholds",
        "source": "ACOG guidance on hypertensive disorders of pregnancy",
        "issuing_body": "American College of Obstetricians and Gynecologists",
        "topic_tags": ["blood_pressure", "diagnosis", "thresholds", "proteinuria"],
        "summary": (
            "ACOG guidance describes blood pressure thresholds and the role of "
            "proteinuria assessment in the evaluation of hypertensive disorders "
            "of pregnancy. Sustained elevated blood pressure readings are central "
            "to clinical evaluation, alongside other signs and symptoms."
        ),
    },
    {
        "id": "nice-symptoms-monitoring",
        "source": "NICE Guideline NG133 (Hypertension in pregnancy)",
        "issuing_body": "National Institute for Health and Care Excellence (UK)",
        "topic_tags": ["symptoms", "headache", "visual_disturbance", "warning_signs"],
        "summary": (
            "Symptoms such as severe headache, visual disturbance, and upper "
            "abdominal pain may indicate progression of hypertensive disease in "
            "pregnancy and warrant prompt clinical assessment. These warning "
            "signs are considered alongside blood pressure and other findings."
        ),
    },
    {
        "id": "gestational-age-context",
        "source": "General obstetric guidance (synthesised summary)",
        "issuing_body": "Demonstration summary — multiple sources",
        "topic_tags": ["gestational_age", "timing", "early_pregnancy"],
        "summary": (
            "Pre-eclampsia typically manifests after 20 weeks of gestation. "
            "Predictive warning signs such as rising blood pressure are less "
            "informative earlier in pregnancy, which is why risk assessment "
            "before 20 weeks relies more heavily on baseline risk factors than "
            "on emerging clinical trends."
        ),
    },
]


def get_guidelines() -> list[dict]:
    """Return the full guidelines corpus."""
    return GUIDELINES


if __name__ == "__main__":
    guidelines = get_guidelines()
    print(f"Guidelines corpus: {len(guidelines)} entries\n")
    for g in guidelines:
        print(f"  [{g['id']}]")
        print(f"    Source: {g['source']}")
        print(f"    Tags: {', '.join(g['topic_tags'])}")
        print(f"    Summary: {g['summary'][:80]}...")
        print()