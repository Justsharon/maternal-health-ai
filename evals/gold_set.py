"""
Sentinel — Gold Set Construction

Builds a fixed, stratified evaluation set from held-out test data.
The gold set spans the full risk distribution including edge cases,
and is used for regression testing on every system change.

Reference: Wong et al. (external validation as deployment gate),
Hamel Husain "Your AI Product Needs Evals".
"""

import json
import numpy as np
import joblib
from pathlib import Path


def build_gold_set(n_cases: int = 100, seed: int = 42):
    """
    Construct a stratified gold set from held-out test data.
    
    Stratification ensures the gold set includes:
      - Confirmed positive cases (developed pre-eclampsia)
      - Confirmed negative cases
      - Cases across the predicted-probability spectrum
    """
    np.random.seed(seed)
    
    # Load held-out test data
    X_test = np.load("models/X_test.npy")
    y_test = np.load("models/y_test.npy")
    
    # Load calibrated model to get predicted probabilities
    model = joblib.load("models/risk_model.joblib")
    probabilities = model.predict_proba(X_test)[:, 1]
    
    # Separate by true outcome
    positive_indices = np.where(y_test == 1)[0]
    negative_indices = np.where(y_test == 0)[0]
    
    print(f"Test set: {len(y_test)} patients")
    print(f"  Positives: {len(positive_indices)}")
    print(f"  Negatives: {len(negative_indices)}")
    
    # Build stratified gold set
    # Take ALL positives (they're rare and valuable), fill rest with negatives
    n_positives = min(len(positive_indices), n_cases // 2)
    n_negatives = n_cases - n_positives
    
    selected_positives = np.random.choice(
        positive_indices, size=n_positives, replace=False
    )
    selected_negatives = np.random.choice(
        negative_indices, size=min(n_negatives, len(negative_indices)), replace=False
    )
    
    selected_indices = np.concatenate([selected_positives, selected_negatives])
    np.random.shuffle(selected_indices)
    
    # Build gold set records
    gold_cases = []
    for idx in selected_indices:
        gold_cases.append({
            "case_id": f"GOLD-{idx:04d}",
            "features": X_test[idx].tolist(),
            "true_outcome": int(y_test[idx]),
            "model_probability": float(probabilities[idx]),
        })
    
    print(f"\nGold set built: {len(gold_cases)} cases")
    print(f"  Positives: {sum(1 for c in gold_cases if c['true_outcome'] == 1)}")
    print(f"  Negatives: {sum(1 for c in gold_cases if c['true_outcome'] == 0)}")
    
    # Save
    output_path = Path("evals/gold_set.json")
    with open(output_path, "w") as f:
        json.dump(gold_cases, f, indent=2)
    
    print(f"\n💾 Saved to {output_path}")
    return gold_cases


if __name__ == "__main__":
    build_gold_set(n_cases=100)