"""
Sentinel — Synthetic Patient Generator

Generates longitudinal pregnancy records with realistic epidemiological
patterns and embedded fairness test signals.

Reference: Synthea design principles (longitudinal records, realistic 
correlations) and published maternal health epidemiology.
"""

import random
import json
from pathlib import Path
from typing import Optional

import numpy as np
from data.schema import (
    PatientRecord,
    BloodPressureReading,
    Symptoms,
    Ethnicity,
    DiabetesType,
    SocioeconomicProxy,
)


# --- Population distribution parameters ---

ETHNICITY_DISTRIBUTION = {
    Ethnicity.BLACK_AFRICAN: 0.25,
    Ethnicity.WHITE: 0.25,
    Ethnicity.SOUTH_ASIAN: 0.20,
    Ethnicity.EAST_ASIAN: 0.15,
    Ethnicity.OTHER: 0.10,
    Ethnicity.NOT_DISCLOSED: 0.05,
}

SOCIOECONOMIC_DISTRIBUTION = {
    SocioeconomicProxy.LOW: 0.30,
    SocioeconomicProxy.MIDDLE: 0.45,
    SocioeconomicProxy.HIGH: 0.20,
    SocioeconomicProxy.NOT_DISCLOSED: 0.05,
}

# --- Risk factor weights (from published literature) ---

# These coefficients approximate documented relative risks
# for pre-eclampsia. Source: NICE guidelines, Fetal Medicine Foundation
BASE_RISK = 0.03  # ~3% baseline incidence


RISK_WEIGHTS = {
    "age_over_35": 1.5,
    "age_under_18": 1.3,
    "nulliparous": 1.4,        # First pregnancy
    "bmi_overweight": 1.3,      # NEW: 25-30
    "bmi_obese": 2.0,          # BMI > 30
    "bmi_morbidly_obese": 3.0, # BMI > 40
    "prior_preeclampsia": 7.0, # Strongest single risk factor
    "family_history": 1.6,
    "multiple_pregnancy": 2.5,
    "pre_existing_hypertension": 4.0,
    "diabetes_any": 2.5,
    "ethnicity_black_african": 1.5,  # Documented disparity
    "ethnicity_south_asian": 1.3,
}

def _sample_weighted(distribution: dict) -> str:
    """Sample one option from a weighted distribution dict."""
    options = list(distribution.keys())
    weights = list(distribution.values())
    return random.choices(options, weights=weights, k=1)[0]


def _calculate_risk_probability(features: dict) -> float:
    """
    Calculate true pre-eclampsia probability for this patient.
    
    This is the GROUND TRUTH the model will learn to predict.
    Uses multiplicative risk model based on documented risk factors.
    """

    risk = BASE_RISK

    if features["age"] >= 35:
        risk *= RISK_WEIGHTS["age_over_35"]
    if features["age"] < 18:
        risk *= RISK_WEIGHTS["age_under_18"]
    if features["parity"] == 0:
        risk *= RISK_WEIGHTS["nulliparous"]
    if features["bmi"] >= 40:
        risk *= RISK_WEIGHTS["bmi_morbidly_obese"]
    elif features["bmi"] >= 30:
        risk *= RISK_WEIGHTS["bmi_obese"]
    elif features["bmi"] >= 25:
        risk *= RISK_WEIGHTS["bmi_overweight"]
    if features["prior_preeclampsia"]:
        risk *= RISK_WEIGHTS["prior_preeclampsia"]
    if features["family_history"]:
        risk *= RISK_WEIGHTS["family_history"]
    if features["multiple_pregnancy"]:
        risk *= RISK_WEIGHTS["multiple_pregnancy"]
    if features["pre_existing_hypertension"]:
        risk *= RISK_WEIGHTS["pre_existing_hypertension"]
    if features["diabetes"] != DiabetesType.NONE:
        risk *= RISK_WEIGHTS["diabetes_any"]
    if features["ethnicity"] == Ethnicity.BLACK_AFRICAN:
        risk *= RISK_WEIGHTS["ethnicity_black_african"]
    if features["ethnicity"] == Ethnicity.SOUTH_ASIAN:
        risk *= RISK_WEIGHTS["ethnicity_south_asian"]
    
    return min(risk, 0.85)

def _generate_bp_trajectory(
    will_develop_preeclampsia: bool,
    current_week: int,
    has_chronic_hypertension: bool,
) -> list[BloodPressureReading]:
    """
    Generate realistic BP trajectory across pregnancy.
    
    Healthy pregnancies show slight BP dip in Q2 then return to baseline.
    Pre-eclamptic pregnancies show progressive BP rise after week 20.
    """

    readings = []

    # Baseline BP (slightly elevated if chronic hypertension)
    if has_chronic_hypertension:
        baseline_systolic = random.randint(135, 150)
        baseline_diastolic = random.randint(85, 95)
    else:
        baseline_systolic = random.randint(105, 125)
        baseline_diastolic = random.randint(65, 80)

    # Generate readings at standard antenatal visit weeks
    visit_weeks = [w for w in [12, 16, 20, 24, 28, 32, 36, 40] if w <= current_week]

    for week in visit_weeks:
        if will_develop_preeclampsia and week >= 20:
            # Pre-eclamptic trajectory: progressive rise after week 20
            weeks_past_20  = week - 20
            systolic_rise = weeks_past_20 * random.uniform(2, 5)
            diastolic_rise = weeks_past_20 * random.uniform(1.5, 3)

            systolic = int(baseline_systolic + systolic_rise + random.uniform(-3, 5))
            diastolic = int(baseline_diastolic + diastolic_rise + random.uniform(-2, 3))
        else:
            # Normal trajectory: slight Q2 dip, return to baseline
            if 14 <= week <= 22:
                # Mid-trimester dip
                systolic = baseline_systolic + random.randint(-8, -2)
                diastolic = baseline_diastolic + random.randint(-5, -1)
            else:
                systolic = baseline_systolic + random.randint(-4, 4)
                diastolic = baseline_diastolic + random.randint(-3, 3)

        # Ensure systolic > diastolic
        if systolic <= diastolic:
            systolic = diastolic + random.randint(20, 35)

        # Clip to physiological ranges
        systolic = max(70, min(systolic, 240))
        diastolic = max(40, min(diastolic, 190))
        
        readings.append(BloodPressureReading(
            gestational_week=week,
            systolic=systolic,
            diastolic=diastolic,
        ))

    return readings

def _generate_symptoms(
    will_develop_preeclampsia: bool,
    current_week: int,
) -> Symptoms:
    """Generate symptoms based on disease state and gestational age."""
    if will_develop_preeclampsia and current_week >= 24:
        return Symptoms(
            headache=random.random() < 0.4,
            visual_disturbance=random.random() < 0.2,
            epigastric_pain=random.random() < 0.15,
            swelling=random.random() < 0.5,
        )
    else:
        return Symptoms(
            headache=random.random() < 0.1,
            visual_disturbance=random.random() < 0.02,
            epigastric_pain=random.random() < 0.03,
            swelling=random.random() < 0.2,
        )
    
def _generate_proteinuria(
    will_develop_preeclampsia: bool,
    current_week: int,
) -> Optional[float]:
    """Generate proteinuria reading. None if not measured this visit."""
    # 60% of visits don't have proteinuria measured
    if random.random() < 0.6:
        return None
    
    if will_develop_preeclampsia and current_week >= 20:
        # Elevated proteinuria for pre-eclampsia
        return round(random.uniform(30, 300), 1)
    else:
        return round(random.uniform(0, 25), 1)
    
def generate_patient(patient_id: str) -> PatientRecord:
    """Generate a single synthetic patient record."""

    # Sample demographics
    ethnicity = _sample_weighted(ETHNICITY_DISTRIBUTION)
    socioeconomic = _sample_weighted(SOCIOECONOMIC_DISTRIBUTION)

    # Maternal age — bimodal distribution (peaks around 25 and 32)
    age = int(np.clip(np.random.normal(loc=29, scale=6), 14, 50))

    # Parity — most patients have 0-2 prior pregnancies
    parity = min(np.random.poisson(0.8), 6)

     # Multiple pregnancy — 1.5% baseline
    multiple_pregnancy = random.random() < 0.015
    
    # BMI — log-normal distribution, mean around 26
    bmi = round(np.clip(np.random.lognormal(3.25, 0.20), 16, 60), 1)
    
    # Medical history (independent probabilities)
    prior_preeclampsia = parity > 0 and random.random() < 0.04
    family_history = random.random() < 0.10
    pre_existing_hypertension = random.random() < 0.03
    
    # Diabetes
    diabetes_roll = random.random()
    if diabetes_roll < 0.005:
        diabetes = DiabetesType.TYPE_1
    elif diabetes_roll < 0.025:
        diabetes = DiabetesType.TYPE_2
    elif diabetes_roll < 0.08:
        diabetes = DiabetesType.GESTATIONAL
    else:
        diabetes = DiabetesType.NONE
    
    
    # Current gestational age — uniform across pregnancy weeks
    current_week = random.randint(12, 40)
    
    # Compute true risk probability for this patient
    features = {
        "age": age,
        "parity": parity,
        "bmi": bmi,
        "prior_preeclampsia": prior_preeclampsia,
        "family_history": family_history,
        "multiple_pregnancy": multiple_pregnancy,
        "pre_existing_hypertension": pre_existing_hypertension,
        "diabetes": diabetes,
        "ethnicity": ethnicity,
    }
    risk_probability = _calculate_risk_probability(features)
    
    # Sample outcome based on true probability
    will_develop = random.random() < risk_probability
    
    # Generate longitudinal data
    bp_readings = _generate_bp_trajectory(
        will_develop_preeclampsia=will_develop,
        current_week=current_week,
        has_chronic_hypertension=pre_existing_hypertension,
    )
    
    symptoms = _generate_symptoms(will_develop, current_week)
    proteinuria = _generate_proteinuria(will_develop, current_week)
    
    # Build the validated record
    return PatientRecord(
        patient_id=patient_id,
        is_synthetic=True,
        age=age,
        ethnicity=ethnicity,
        socioeconomic_proxy=socioeconomic,
        parity=parity,
        multiple_pregnancy=multiple_pregnancy,
        current_gestational_week=current_week,
        pre_existing_hypertension=pre_existing_hypertension,
        diabetes=diabetes,
        prior_preeclampsia=prior_preeclampsia,
        family_history_preeclampsia=family_history,
        bmi_at_booking=bmi,
        blood_pressure_readings=bp_readings,
        proteinuria_level=proteinuria,
        current_symptoms=symptoms,
        developed_preeclampsia_by_32w=will_develop,
    )


def generate_dataset(n_patients: int = 5000, seed: int = 42) -> list[PatientRecord]:
    """Generate a full synthetic dataset."""
    random.seed(seed)
    np.random.seed(seed)

    patients = []
    for i in range(n_patients):
        patient = generate_patient(patient_id=f"SYN-{i:05d}")
        patients.append(patient)
    return patients


def save_dataset(patients: list[PatientRecord], path: str = "synthetic_data.json"):
    """Save dataset to JSON for reuse."""
    data = [p.model_dump(mode="json") for p in patients]
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)
    print(f"Saved {len(patients)} patients to {path}")

def load_dataset(path: str = "synthetic_data.json") -> list[PatientRecord]:
    """Load dataset from JSON."""
    with open(path) as f:
        data = json.load(f)
    return [PatientRecord(**record) for record in data]


# --- Standalone test + dataset analysis ---

if __name__ == "__main__":
    print("Generating synthetic dataset...\n")
    patients = generate_dataset(n_patients=5000)
    
    # Quick statistics
    total = len(patients)
    cases = sum(1 for p in patients if p.developed_preeclampsia_by_32w)
    rate = cases / total * 100
    
    print(f" Dataset Statistics")
    print(f"  Total patients: {total}")
    print(f"  Pre-eclampsia cases: {cases}")
    print(f"  Overall incidence: {rate:.1f}%")
    print()
    
    # Incidence by ethnicity
    print("Incidence by Ethnicity:")
    for ethnicity in Ethnicity:
        subset = [p for p in patients if p.ethnicity == ethnicity]
        if subset:
            cases_in_subset = sum(1 for p in subset if p.developed_preeclampsia_by_32w)
            subset_rate = cases_in_subset / len(subset) * 100
            print(f"  {ethnicity.value:20s} n={len(subset):4d}  rate={subset_rate:.1f}%")
    print()
    
    # Incidence by age group
    print("Incidence by Age Group:")
    age_groups = [(14, 19), (20, 29), (30, 34), (35, 50)]
    for low, high in age_groups:
        subset = [p for p in patients if low <= p.age <= high]
        if subset:
            cases_in_subset = sum(1 for p in subset if p.developed_preeclampsia_by_32w)
            subset_rate = cases_in_subset / len(subset) * 100
            print(f"  Age {low}-{high:2d}  n={len(subset):4d}  rate={subset_rate:.1f}%")
    print()
    
    # Incidence by BMI category
    print("Incidence by BMI Category:")
    bmi_groups = [("Normal <25", 0, 25), ("Overweight 25-30", 25, 30), 
                  ("Obese 30-40", 30, 40), ("Morbid 40+", 40, 100)]
    for label, low, high in bmi_groups:
        subset = [p for p in patients if low <= p.bmi_at_booking < high]
        if subset:
            cases_in_subset = sum(1 for p in subset if p.developed_preeclampsia_by_32w)
            subset_rate = cases_in_subset / len(subset) * 100
            print(f"  {label:20s} n={len(subset):4d}  rate={subset_rate:.1f}%")
    print()
    
    # Save for reuse
    save_dataset(patients)
    
    # Sample 3 records to verify
    print("\n Sample patients:")
    for p in random.sample(patients, 3):
        outcome = "PRE-ECLAMPSIA" if p.developed_preeclampsia_by_32w else "Normal"
        print(f"\n  {p.patient_id}: {outcome}")
        print(f"    Age: {p.age}, Ethnicity: {p.ethnicity.value}")
        print(f"    BMI: {p.bmi_at_booking}, Parity: {p.parity}")
        print(f"    Current week: {p.current_gestational_week}")
        print(f"    BP readings: {len(p.blood_pressure_readings)}")
        if p.blood_pressure_readings:
            last_bp = p.blood_pressure_readings[-1]
            print(f"    Latest BP: {last_bp.systolic}/{last_bp.diastolic} at week {last_bp.gestational_week}")