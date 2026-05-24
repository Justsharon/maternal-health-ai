"""
Sentinel — SHAP-based Risk Explainer

Generates per-patient explanations of risk predictions using SHAP values.
Each prediction is decomposed into:
  - Base value (average model prediction across all patients)
  - Feature contributions (how each input pushed risk up or down)

Reference: Christoph Molnar's "Interpretable Machine Learning" Chapter 5.10,
WHO Principle 3 (explainability and intelligibility).
"""

import joblib
import numpy as np
import shap
from typing import Optional

from data.schema import PatientRecord
from models.feature_extractor import extract_features, FEATURE_NAMES


# --- Plain-language mapping for features ---
# Maps technical feature names to clinician-readable descriptions

FEATURE_LABELS = {
    "age": "maternal age",
    "ethnicity_black_african": "ethnicity (Black African)",
    "ethnicity_white": "ethnicity (White)",
    "ethnicity_south_asian": "ethnicity (South Asian)",
    "ethnicity_east_asian": "ethnicity (East Asian)",
    "ethnicity_other": "ethnicity (other)",
    "socioeconomic_low": "low socioeconomic status",
    "socioeconomic_middle": "middle socioeconomic status",
    "socioeconomic_high": "high socioeconomic status",
    "parity": "number of previous pregnancies",
    "is_nulliparous": "first pregnancy",
    "multiple_pregnancy": "multiple pregnancy (twins/triplets)",
    "current_gestational_week": "current gestational age",
    "pre_existing_hypertension": "pre-existing hypertension",
    "diabetes_any": "diabetes (any type)",
    "prior_preeclampsia": "prior pre-eclampsia",
    "family_history_preeclampsia": "family history of pre-eclampsia",
    "bmi_at_booking": "BMI at booking",
    "bmi_obese": "BMI in obese range (≥30)",
    "bmi_morbidly_obese": "BMI in morbidly obese range (≥40)",
    "bp_readings_count": "number of BP readings",
    "bp_latest_systolic": "latest systolic BP",
    "bp_latest_diastolic": "latest diastolic BP",
    "bp_max_systolic": "highest systolic BP",
    "bp_max_diastolic": "highest diastolic BP",
    "bp_mean_systolic": "average systolic BP",
    "bp_mean_diastolic": "average diastolic BP",
    "bp_systolic_range": "systolic BP range",
    "bp_diastolic_range": "diastolic BP range",
    "bp_systolic_change": "systolic BP change across pregnancy",
    "bp_diastolic_change": "diastolic BP change across pregnancy",
    "bp_rising_trend": "rising BP trajectory",
    "proteinuria_level": "proteinuria level",
    "has_proteinuria_measurement": "proteinuria measured",
    "any_symptoms": "any symptoms reported",
    "symptom_count": "number of symptoms",
}


class RiskExplainer:
    """Wraps SHAP explainability around the trained risk model."""

    def __init__(
        self,
        calibrated_model_path: str = "models/risk_model.joblib",
        base_model_path: str = "models/risk_model_base.joblib",
    ):
        # Calibrated model gives correct probabilities
        self.calibrated_model = joblib.load(calibrated_model_path)
        # Base model is used for SHAP (TreeExplainer can read it)
        self.base_model = joblib.load(base_model_path)
        self.explainer = shap.TreeExplainer(self.base_model)

        # Compute empirical base probability from calibrated model
        self._compute_empirical_base_value()

    def _compute_empirical_base_value(self):
        """Base probability = mean calibrated prediction across population."""
        from data.generator import load_dataset
        from models.feature_extractor import build_feature_matrix

        patients = load_dataset("synthetic_data.json")
        X, _ = build_feature_matrix(patients)

        all_probabilities = self.calibrated_model.predict_proba(X)[:, 1]
        self.base_probability = float(all_probabilities.mean())

    def explain(self, record: PatientRecord, top_k: int = 6) -> dict:
        x = extract_features(record).reshape(1, -1)

        # Use CALIBRATED model for the probability shown to clinicians
        probability = float(self.calibrated_model.predict_proba(x)[0, 1])
        # Cap extreme predictions — no responsible clinical tool claims certainty
        probability = min(probability, 0.95)
        probability = max(probability, 0.01)

        # Use BASE model for SHAP feature contributions
        shap_values = self.explainer.shap_values(x)
        if isinstance(shap_values, list):
            shap_values = shap_values[1]
        shap_values = shap_values[0]

        base_probability = self.base_probability

        feature_count = min(len(shap_values), len(FEATURE_NAMES))
        contributions = []
        for i in range(feature_count):
            name = FEATURE_NAMES[i]
            value = float(shap_values[i])
            contributions.append({
                "feature": name,
                "label": FEATURE_LABELS.get(name, name),
                "shap_value": value,
                "direction": "increases risk" if value > 0 else "decreases risk",
                "abs_value": abs(value),
            })

        contributions.sort(key=lambda c: c["abs_value"], reverse=True)

        return {
            "probability": probability,
            "base_probability": base_probability,
            "top_contributions": contributions[:top_k],
            "all_contributions": contributions,
        }


def format_explanation(explanation: dict) -> str:
    """Convert explanation dict to readable clinical narrative."""
    prob = explanation["probability"]
    base = explanation["base_probability"]

    lines = []
    lines.append(f"Risk prediction: {prob:.1%}")
    lines.append(f"Population baseline: {base:.1%}")
    lines.append(f"Difference from baseline: {(prob - base):+.1%}")
    lines.append("")
    lines.append("Top contributing factors:")

    for c in explanation["top_contributions"]:
        direction_symbol = "↑" if c["shap_value"] > 0 else "↓"
        # SHAP values are in log-odds space — for display we show their absolute magnitude
        magnitude = abs(c["shap_value"])
        if magnitude > 0.01:  # filter out trivial contributions
            lines.append(
                f"  {direction_symbol} {c['label']:40s} "
                f"(SHAP: {c['shap_value']:+.3f})"
            )

    return "\n".join(lines)


if __name__ == "__main__":
    from data.generator import load_dataset

    print("Loading dataset and risk model...")
    patients = load_dataset("synthetic_data.json")
    explainer = RiskExplainer()

    print(f"\nBase probability (empirical): {explainer.base_probability:.1%}")
    
    # Find one high-risk and one low-risk patient for comparison
    print("\nFinding example patients...")
    high_risk_patient = None
    low_risk_patient = None

    for p in patients[:500]:
        explanation = explainer.explain(p)
        if explanation["probability"] > 0.6 and high_risk_patient is None:
            high_risk_patient = (p, explanation)
        elif explanation["probability"] < 0.05 and low_risk_patient is None:
            low_risk_patient = (p, explanation)
        if high_risk_patient and low_risk_patient:
            break

    if high_risk_patient:
        p, exp = high_risk_patient
        print(f"\n{'='*70}")
        print(f"HIGH-RISK PATIENT: {p.patient_id}")
        print(
            f"  Age: {p.age}, Ethnicity: {p.ethnicity.value}, BMI: {p.bmi_at_booking}")
        print(
            f"  Parity: {p.parity}, Current week: {p.current_gestational_week}")
        print(f"  Prior pre-eclampsia: {p.prior_preeclampsia}")
        print(
            f"  Actual outcome: {'PRE-ECLAMPSIA' if p.developed_preeclampsia_by_32w else 'normal'}")
        print(f"{'='*70}")
        print(format_explanation(exp))

    if low_risk_patient:
        p, exp = low_risk_patient
        print(f"\n{'='*70}")
        print(f"LOW-RISK PATIENT: {p.patient_id}")
        print(
            f"  Age: {p.age}, Ethnicity: {p.ethnicity.value}, BMI: {p.bmi_at_booking}")
        print(
            f"  Parity: {p.parity}, Current week: {p.current_gestational_week}")
        print(f"  Prior pre-eclampsia: {p.prior_preeclampsia}")
        print(
            f"  Actual outcome: {'PRE-ECLAMPSIA' if p.developed_preeclampsia_by_32w else 'normal'}")
        print(f"{'='*70}")
        print(format_explanation(exp))
