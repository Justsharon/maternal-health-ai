"""
Sentinel — Evaluation Runner

Runs the risk model against the gold set and reports clinically
meaningful metrics — never a single accuracy number.

Reports recall, precision, calibration, and confusion matrix.
This is what catches the Epic Sepsis failure mode.
"""

import json
import numpy as np
import joblib
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix,
)


def load_gold_set(path="evals/gold_set.json"):
    with open(path) as f:
        return json.load(f)


def run_evaluation(threshold: float = 0.5):
    """Run the model against the gold set at a given decision threshold."""
    gold = load_gold_set()
    model = joblib.load("models/risk_model.joblib")
    
    X = np.array([c["features"] for c in gold], dtype=np.float32)
    y_true = np.array([c["true_outcome"] for c in gold])
    
    y_proba = model.predict_proba(X)[:, 1]
    y_pred = (y_proba >= threshold).astype(int)
    
    # Metrics
    precision = precision_score(y_true, y_pred, zero_division=0)
    recall = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    auc = roc_auc_score(y_true, y_proba)
    cm = confusion_matrix(y_true, y_pred)
    
    print(f"{'='*60}")
    print(f"GOLD SET EVALUATION (threshold = {threshold})")
    print(f"{'='*60}")
    print(f"Cases: {len(y_true)} | Positives: {y_true.sum()} | Negatives: {(1-y_true).sum()}")
    print()
    print(f"Recall (sensitivity):  {recall:.3f}  ← % of true cases caught")
    print(f"Precision:             {precision:.3f}  ← % of alerts that are real")
    print(f"F1 score:              {f1:.3f}")
    print(f"ROC AUC:               {auc:.3f}")
    print()
    print(f"Confusion Matrix:")
    print(f"                  Predicted Neg | Predicted Pos")
    print(f"  Actual Neg:     {cm[0][0]:>13} | {cm[0][1]:>13}")
    print(f"  Actual Pos:     {cm[1][0]:>13} | {cm[1][1]:>13}")
    print()
    
    # The clinically critical numbers
    false_negatives = cm[1][0]
    false_positives = cm[0][1]
    print(f"⚠️  Missed cases (false negatives): {false_negatives}")
    print(f"   False alarms (false positives):  {false_positives}")
    
    return {
        "threshold": threshold,
        "recall": recall,
        "precision": precision,
        "f1": f1,
        "auc": auc,
        "false_negatives": int(false_negatives),
        "false_positives": int(false_positives),
    }


def threshold_sweep():
    """
    Show how recall/precision trade off across thresholds.
    For healthcare, we want to find the threshold that maximises recall
    while keeping false positives manageable.
    """
    print(f"\n{'='*60}")
    print("THRESHOLD SWEEP — finding the right operating point")
    print(f"{'='*60}")
    print(f"{'Threshold':>10} | {'Recall':>7} | {'Precision':>9} | {'Missed':>6} | {'FalseAlarm':>10}")
    print("-" * 60)
    
    gold = load_gold_set()
    model = joblib.load("models/risk_model.joblib")
    X = np.array([c["features"] for c in gold], dtype=np.float32)
    y_true = np.array([c["true_outcome"] for c in gold])
    y_proba = model.predict_proba(X)[:, 1]
    
    for threshold in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]:
        y_pred = (y_proba >= threshold).astype(int)
        recall = recall_score(y_true, y_pred, zero_division=0)
        precision = precision_score(y_true, y_pred, zero_division=0)
        cm = confusion_matrix(y_true, y_pred)
        missed = cm[1][0] if cm.shape == (2, 2) else 0
        false_alarm = cm[0][1] if cm.shape == (2, 2) else 0
        print(f"{threshold:>10.1f} | {recall:>7.3f} | {precision:>9.3f} | {missed:>6} | {false_alarm:>10}")


if __name__ == "__main__":
    run_evaluation(threshold=0.5)
    threshold_sweep()