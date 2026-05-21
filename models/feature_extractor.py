"""
Sentinel — Feature Extractor

Converts validated PatientRecord objects into numeric feature vectors
for the risk model. Engineers trajectory features from longitudinal data.

Reference: Synthea principles (trajectories matter), clinical risk
stratification (NICE guidelines, Fetal Medicine Foundation calculator).
"""

import numpy as np
from data.schema import PatientRecord, Ethnicity, DiabetesType, SocioeconomicProxy


# Feature names in canonical order — used for SHAP labels later
FEATURE_NAMES = [
    # Demographics
    "age",
    "ethnicity_black_african",
    "ethnicity_white",
    "ethnicity_south_asian",
    "ethnicity_east_asian",
    "ethnicity_other",
    "socioeconomic_low",
    "socioeconomic_middle",
    "socioeconomic_high",
    
    # Pregnancy context
    "parity",
    "is_nulliparous",
    "multiple_pregnancy",
    "current_gestational_week",
    
    # Medical history
    "pre_existing_hypertension",
    "diabetes_any",
    "prior_preeclampsia",
    "family_history_preeclampsia",
    "bmi_at_booking",
    "bmi_obese",
    "bmi_morbidly_obese",
    
    # BP trajectory features
    "bp_readings_count",
    "bp_latest_systolic",
    "bp_latest_diastolic",
    "bp_max_systolic",
    "bp_max_diastolic",
    "bp_mean_systolic",
    "bp_mean_diastolic",
    "bp_systolic_range",
    "bp_diastolic_range",
    "bp_systolic_change",  # last - first
    "bp_diastolic_change",
    "bp_rising_trend",  # boolean
    
    # Other clinical
    "proteinuria_level",
    "has_proteinuria_measurement",
    "any_symptoms",
    "symptom_count",
]


def extract_features(record: PatientRecord) -> np.ndarray:
    """
    Convert a PatientRecord to a feature vector for the risk model.
    
    Returns numpy array of features in canonical order.
    Missing values use -1.0 sentinel (XGBoost handles natively).
    """
    features = []
    
    # --- Demographics ---
    features.append(float(record.age))
    
    # One-hot ethnicity (excluding NOT_DISCLOSED as reference category)
    features.append(float(record.ethnicity == Ethnicity.BLACK_AFRICAN))
    features.append(float(record.ethnicity == Ethnicity.WHITE))
    features.append(float(record.ethnicity == Ethnicity.SOUTH_ASIAN))
    features.append(float(record.ethnicity == Ethnicity.EAST_ASIAN))
    features.append(float(record.ethnicity == Ethnicity.OTHER))
    
    # One-hot socioeconomic
    features.append(float(record.socioeconomic_proxy == SocioeconomicProxy.LOW))
    features.append(float(record.socioeconomic_proxy == SocioeconomicProxy.MIDDLE))
    features.append(float(record.socioeconomic_proxy == SocioeconomicProxy.HIGH))
    
    # --- Pregnancy context ---
    features.append(float(record.parity))
    features.append(float(record.parity == 0))
    features.append(float(record.multiple_pregnancy))
    features.append(float(record.current_gestational_week))
    
    # --- Medical history ---
    features.append(float(record.pre_existing_hypertension))
    features.append(float(record.diabetes != DiabetesType.NONE))
    features.append(float(record.prior_preeclampsia))
    features.append(float(record.family_history_preeclampsia))
    features.append(float(record.bmi_at_booking))
    features.append(float(record.bmi_at_booking >= 30))
    features.append(float(record.bmi_at_booking >= 40))
    
    # --- BP trajectory features ---
    bp_systolic = [r.systolic for r in record.blood_pressure_readings]
    bp_diastolic = [r.diastolic for r in record.blood_pressure_readings]
    
    if bp_systolic:
        features.append(float(len(bp_systolic)))
        features.append(float(bp_systolic[-1]))
        features.append(float(bp_diastolic[-1]))
        features.append(float(max(bp_systolic)))
        features.append(float(max(bp_diastolic)))
        features.append(float(np.mean(bp_systolic)))
        features.append(float(np.mean(bp_diastolic)))
        features.append(float(max(bp_systolic) - min(bp_systolic)))
        features.append(float(max(bp_diastolic) - min(bp_diastolic)))
        features.append(float(bp_systolic[-1] - bp_systolic[0]))
        features.append(float(bp_diastolic[-1] - bp_diastolic[0]))
        # Rising trend: more than 10 mmHg systolic rise
        features.append(float((bp_systolic[-1] - bp_systolic[0]) > 10))
    else:
        # No BP readings — fill with sentinel
        features.extend([0.0] + [-1.0] * 11)
    
    # --- Other clinical ---
    if record.proteinuria_level is not None:
        features.append(float(record.proteinuria_level))
        features.append(1.0)
    else:
        features.append(-1.0)
        features.append(0.0)
    
    s = record.current_symptoms
    symptom_count = (
        int(s.headache) + int(s.visual_disturbance) + 
        int(s.epigastric_pain) + int(s.swelling)
    )
    features.append(float(symptom_count > 0))
    features.append(float(symptom_count))
    
    return np.array(features, dtype=np.float32)


def build_feature_matrix(records: list[PatientRecord]) -> tuple[np.ndarray, np.ndarray]:
    """
    Build full feature matrix X and label vector y for training.
    Returns (X, y) where X is (n_samples, n_features) and y is (n_samples,).
    """
    X = np.vstack([extract_features(r) for r in records])
    y = np.array([
        int(r.developed_preeclampsia_by_32w) 
        for r in records
    ], dtype=np.int32)
    return X, y


if __name__ == "__main__":
    from data.generator import load_dataset
    
    print("Loading synthetic dataset...")
    patients = load_dataset("synthetic_data.json")
    
    print(f"Extracting features from {len(patients)} patients...")
    X, y = build_feature_matrix(patients)
    
    print(f"\n Feature Matrix")
    print(f"  Shape: {X.shape}")
    print(f"  Features: {len(FEATURE_NAMES)}")
    print(f"  Positive cases (pre-eclampsia): {y.sum()} ({y.mean()*100:.1f}%)")
    print(f"  Negative cases: {(1-y).sum()} ({(1-y).mean()*100:.1f}%)")
    
    # Spot check feature values for one patient
    print(f"\n Sample patient feature vector (first 10 features):")
    for name, value in list(zip(FEATURE_NAMES, X[0]))[:10]:
        print(f"  {name:30s} = {value:.2f}")