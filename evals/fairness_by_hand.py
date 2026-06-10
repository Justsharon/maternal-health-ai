"""
Sentinel — Equalized Odds, Computed By Hand

Before using Fairlearn, we compute the core metric manually so we
understand exactly what it measures. Equalized odds = equal True Positive
Rate (recall) AND equal False Positive Rate across demographic groups.

This is the metric we TRUST for Sentinel because it conditions on the
true outcome — it asks "are equally-sick patients caught equally well?",
which is fair regardless of differing base rates across groups.
"""

import numpy as np
import joblib
from data.generator import load_dataset
from models.feature_extractor import build_feature_matrix, extract_features


def compute_rates(y_true, y_pred):
    """
    True Positive Rate (recall) and False Positive Rate.
    TPR = TP / (TP + FN)  — of actually-positive, how many caught
    FPR = FP / (FP + TN)  — of actually-negative, how many falsely flagged
    Big-O: O(n) single pass. Memory: O(1).
    """
    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    tn = int(np.sum((y_pred == 0) & (y_true == 0)))

    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return tpr, fpr, (tp, fn, fp, tn)


if __name__ == "__main__":
    THRESHOLD = 0.1  # Sentinel's operating threshold (from Day 5 decision)

    patients = load_dataset("synthetic_data.json")
    model = joblib.load("models/risk_model.joblib")

    # Predict for every patient
    X, y_true = build_feature_matrix(patients)
    y_proba = model.predict_proba(X)[:, 1]
    y_pred = (y_proba >= THRESHOLD).astype(int)

    # Group by ethnicity (the protected attribute we care most about)
    print(f"Equalized Odds by Ethnicity (threshold = {THRESHOLD})")
    print("=" * 70)
    print(f"{'Group':<18} {'n':>5} {'TPR(recall)':>12} {'FPR':>8} {'true_rate':>10}")
    print("-" * 70)

    group_tprs = {}
    group_fprs = {}

    ethnicities = sorted(set(p.ethnicity.value for p in patients))
    for eth in ethnicities:
        idx = [i for i, p in enumerate(patients) if p.ethnicity.value == eth]
        if not idx:
            continue
        yt = y_true[idx]
        yp = y_pred[idx]
        tpr, fpr, _ = compute_rates(yt, yp)
        true_rate = yt.mean()
        group_tprs[eth] = tpr
        group_fprs[eth] = fpr
        print(f"{eth:<18} {len(idx):>5} {tpr:>12.3f} {fpr:>8.3f} {true_rate:>10.3f}")

    # Equalized odds difference = the worst gap across groups
    tpr_gap = max(group_tprs.values()) - min(group_tprs.values())
    fpr_gap = max(group_fprs.values()) - min(group_fprs.values())

    print("-" * 70)
    print(f"\nEqualized Odds Differences (lower = fairer):")
    print(f"  TPR gap (recall disparity): {tpr_gap:.3f}")
    print(f"  FPR gap (false-alarm disparity): {fpr_gap:.3f}")
    print(f"\n  Worst-served group (lowest recall): "
          f"{min(group_tprs, key=group_tprs.get)} "
          f"({min(group_tprs.values()):.3f})")
    print(f"  Best-served group (highest recall): "
          f"{max(group_tprs, key=group_tprs.get)} "
          f"({max(group_tprs.values()):.3f})")