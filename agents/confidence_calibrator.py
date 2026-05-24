"""
Sentinel — Confidence Calibrator (Agent 3)

Annotates risk predictions with reliability information. Does NOT change
the probability — it tells the clinician how much to trust it for THIS
patient.

Two reliability checks:
  1. Gestational window — predictions before week 20 have limited signal
  2. Out-of-distribution — unusual feature combinations reduce reliability

Reference: Wong et al. (knowing when a model operates outside its
validated range), the early-pregnancy limitation discovered in eval.
"""

import numpy as np
import joblib
from state import SentinelState
from models.feature_extractor import extract_features
from data.schema import PatientRecord


# Gestational week below which BP-trajectory signal is limited
RELIABLE_GESTATIONAL_WEEK = 20

# How far outside training feature ranges counts as out-of-distribution
OOD_STD_THRESHOLD = 3.0


class ConfidenceCalibrator:
    """Computes reliability annotations for risk predictions."""
    
    def __init__(self):
        # Load training feature statistics for OOD detection
        self._compute_training_stats()
    
    def _compute_training_stats(self):
        """Compute per-feature mean and std from training data for OOD checks."""
        from data.generator import load_dataset
        from models.feature_extractor import build_feature_matrix
        
        patients = load_dataset("synthetic_data.json")
        X, _ = build_feature_matrix(patients)
        
        self.feature_means = X.mean(axis=0)
        self.feature_stds = X.std(axis=0)
        # Avoid division by zero for constant features
        self.feature_stds[self.feature_stds == 0] = 1.0
    
    def _check_gestational_window(self, record: PatientRecord) -> tuple[bool, str]:
        """Check if patient is in the strong-signal gestational window."""
        week = record.current_gestational_week
        if week < RELIABLE_GESTATIONAL_WEEK:
            return False, (
                f"Patient is at gestational week {week}. Sentinel's primary "
                f"predictive signal (BP trajectory) is limited before week "
                f"{RELIABLE_GESTATIONAL_WEEK}. Predictions in this window carry "
                f"higher uncertainty regardless of the displayed probability. "
                f"Continue standard risk-factor screening."
            )
        return True, ""
    
    def _check_out_of_distribution(self, features: np.ndarray) -> tuple[bool, str]:
        """Check if patient features fall far outside training distribution."""
        z_scores = np.abs((features - self.feature_means) / self.feature_stds)
        max_z = float(np.max(z_scores))
        n_outlier_features = int(np.sum(z_scores > OOD_STD_THRESHOLD))
        
        if n_outlier_features > 0:
            return False, (
                f"Patient has {n_outlier_features} feature(s) outside the "
                f"typical training range (max deviation {max_z:.1f} standard "
                f"deviations). This patient is atypical relative to the data "
                f"Sentinel was validated on; treat the prediction with caution."
            )
        return True, ""
    
    def calibrate(self, record: PatientRecord, risk_probability: float) -> dict:
        """
        Compute reliability annotation for a prediction.
        
        Returns dict with confidence, reliability_flag, reliability_reason.
        """
        features = extract_features(record)
        
        window_ok, window_msg = self._check_gestational_window(record)
        dist_ok, dist_msg = self._check_out_of_distribution(features)
        
        # Build reliability assessment
        reasons = []
        if not window_ok:
            reasons.append(window_msg)
        if not dist_ok:
            reasons.append(dist_msg)
        
        if window_ok and dist_ok:
            reliability_flag = "reliable"
            # Confidence is high — derived from how far the probability is
            # from the uncertain middle (0.5)
            confidence = float(abs(risk_probability - 0.5) * 2)
            reliability_reason = None
        else:
            reliability_flag = "reduced_reliability"
            # Reduced confidence when outside validated regime
            confidence = float(abs(risk_probability - 0.5) * 2 * 0.5)  # halved
            reliability_reason = " ".join(reasons)
        
        return {
            "confidence": round(confidence, 3),
            "reliability_flag": reliability_flag,
            "reliability_reason": reliability_reason,
        }


# Module-level singleton (load stats once)
_calibrator = None


def confidence_calibrator(state: SentinelState) -> SentinelState:
    """
    Agent 3 — annotate the prediction with reliability information.
    
    Reads:  validated_record, risk_probability
    Writes: confidence, reliability_flag, reliability_reason
    """
    global _calibrator
    if _calibrator is None:
        _calibrator = ConfidenceCalibrator()
    
    record = PatientRecord(**state["validated_record"])
    risk_probability = state["risk_probability"]
    
    result = _calibrator.calibrate(record, risk_probability)
    
    state["confidence"] = result["confidence"]
    state["reliability_flag"] = result["reliability_flag"]
    state["reliability_reason"] = result["reliability_reason"]
    
    return state


# --- Standalone test ---
if __name__ == "__main__":
    from data.generator import load_dataset
    
    calibrator = ConfidenceCalibrator()
    patients = load_dataset("synthetic_data.json")
    model = joblib.load("models/risk_model.joblib")
    
    # Find test cases
    early_patient = None      # week < 20
    late_patient = None       # week >= 20
    
    for p in patients:
        if p.current_gestational_week < 18 and early_patient is None:
            early_patient = p
        elif p.current_gestational_week >= 28 and late_patient is None:
            late_patient = p
        if early_patient and late_patient:
            break
    
    for label, patient in [("EARLY PREGNANCY", early_patient), ("LATE PREGNANCY", late_patient)]:
        features = extract_features(patient).reshape(1, -1)
        prob = float(model.predict_proba(features)[0, 1])
        result = calibrator.calibrate(patient, prob)
        
        print(f"{'='*65}")
        print(f"{label} — {patient.patient_id}")
        print(f"  Gestational week: {patient.current_gestational_week}")
        print(f"  Risk probability: {prob:.1%}")
        print(f"  Confidence: {result['confidence']}")
        print(f"  Reliability: {result['reliability_flag']}")
        if result['reliability_reason']:
            print(f"  Reason: {result['reliability_reason'][:120]}...")
        print()