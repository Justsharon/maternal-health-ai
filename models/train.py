"""
Sentinel — Risk Prediction Model Training

Trains an XGBoost classifier to predict pre-eclampsia risk from
engineered patient features.

Engineering decisions:
1. Stratified train/val/test split (preserves class balance)
2. Regularisation via max_depth, learning_rate, early stopping
3. Class weighting for the 92:8 imbalance
4. Hold-out test set reserved for Day 7 calibration evaluation
"""

import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)
import joblib
from sklearn.calibration import CalibratedClassifierCV

from data.generator import load_dataset
from models.feature_extractor import build_feature_matrix, FEATURE_NAMES

# --- Hyperparameters ---
XGBOOST_PARAMS = {
    "objective": "binary:logistic",  # predict probability
    "max_depth": 4,                  # regularisation: shallow trees
    "learning_rate": 0.05,           # regularisation: slow learning
    "n_estimators": 500,             # upper bound; early stopping cuts short
    "min_child_weight": 5,           # regularisation: minimum leaf samples
    "subsample": 0.8,                # use 80% of data per tree (regularisation)
    "colsample_bytree": 0.8,         # use 80% of features per tree
    "random_state": 42,
    "eval_metric": "auc",
    "early_stopping_rounds": 20,
}

def split_data(X, y, seed=42):
    """
    Three-way stratified split:
      70% training
      15% validation (for early stopping)
      15% test (held out for final evaluation)
    """
    # First split: 85% train+val, 15% test
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=0.15, stratify=y, random_state=seed
    )

    # Second split: from the 85%, take 15/85 = ~17.6% as validation
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=0.176, stratify=y_trainval, random_state=seed
    )

    return X_train, X_val, X_test, y_train, y_val, y_test

def compute_class_weight(y_train):
    """Compute scale_pos_weight for imbalanced classes."""
    n_neg = (y_train == 0).sum()
    n_pos = (y_train == 1).sum()
    return n_neg / n_pos if n_pos > 0 else 1.0


def evaluate(y_true, y_pred_proba, threshold=0.5, label="Test"):
    """Print evaluation metrics for a set of predictions."""
    y_pred = (y_pred_proba >= threshold).astype(int)
    
    print(f"\n {label} Set Performance")
    print(f"  Total samples: {len(y_true)}")
    print(f"  Actual positives: {y_true.sum()} ({y_true.mean()*100:.1f}%)")
    print(f"  Predicted positives (threshold={threshold}): {y_pred.sum()}")
    print()
    print(f"  Accuracy:   {accuracy_score(y_true, y_pred):.3f}")
    print(f"  Precision:  {precision_score(y_true, y_pred, zero_division=0):.3f}")
    print(f"  Recall:     {recall_score(y_true, y_pred):.3f}")
    print(f"  F1 score:   {f1_score(y_true, y_pred):.3f}")
    print(f"  ROC AUC:    {roc_auc_score(y_true, y_pred_proba):.3f}")
    
    print(f"\n  Confusion Matrix:")
    cm = confusion_matrix(y_true, y_pred)
    print(f"                 Predicted Neg | Predicted Pos")
    print(f"  Actual Neg:    {cm[0][0]:>13} | {cm[0][1]:>13}")
    print(f"  Actual Pos:    {cm[1][0]:>13} | {cm[1][1]:>13}")


def train():
    """Full training pipeline."""
    print("Loading dataset...")
    patients = load_dataset("synthetic_data.json")
    
    print("Extracting features...")
    X, y = build_feature_matrix(patients)
    print(f"  Total samples: {len(X)}")
    print(f"  Features: {X.shape[1]}")
    
    print("\nSplitting into train/val/test (70/15/15 stratified)...")
    X_train, X_val, X_test, y_train, y_val, y_test = split_data(X, y)
    print(f"  Train: {len(X_train)} ({y_train.mean()*100:.1f}% positive)")
    print(f"  Val:   {len(X_val)} ({y_val.mean()*100:.1f}% positive)")
    print(f"  Test:  {len(X_test)} ({y_test.mean()*100:.1f}% positive)")
    
    # Class imbalance handling
    scale_pos_weight = compute_class_weight(y_train)
    print(f"\nClass imbalance: scale_pos_weight = {scale_pos_weight:.2f}")
    
    # Build model
    # Build base model with class weighting
    print("\nTraining XGBoost base classifier...")
    base_model = xgb.XGBClassifier(
        **XGBOOST_PARAMS,
        scale_pos_weight=scale_pos_weight,
    )

    base_model.fit(
        X_train, y_train,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

    print(f"  Base model trees built: {base_model.best_iteration + 1}")
    print(f"  Base model validation AUC: {base_model.best_score:.3f}")

    # Wrap with calibration layer
    # CalibratedClassifierCV uses the validation set to learn the mapping
    # from decision scores to calibrated probabilities
    print("\nCalibrating probabilities...")
    try:
    # scikit-learn 1.6+ uses FrozenEstimator
        from sklearn.frozen import FrozenEstimator
        model = CalibratedClassifierCV(
            FrozenEstimator(base_model),
            method="isotonic",
        )
        model.fit(X_val, y_val)
    except ImportError:
        # Older scikit-learn versions support cv="prefit"
        model = CalibratedClassifierCV(
            base_model,
            method="isotonic",
            cv="prefit",
        )
        model.fit(X_val, y_val)

    print("  Calibration complete.")
    
    print(f"  Base model trees built: {base_model.best_iteration + 1}")
    print(f"  Base model validation AUC: {base_model.best_score:.3f}")
    
    # Evaluate on all three splits
    train_proba = model.predict_proba(X_train)[:, 1]
    val_proba = model.predict_proba(X_val)[:, 1]
    test_proba = model.predict_proba(X_test)[:, 1]
    
    evaluate(y_train, train_proba, label="Training")
    evaluate(y_val, val_proba, label="Validation")
    evaluate(y_test, test_proba, label="Test")
    
    # Save model and test set for later use
    print("\n Saving model and test set...")
    joblib.dump(base_model, "models/risk_model_base.joblib")  # uncalibrated, for SHAP
    joblib.dump(model, "models/risk_model.joblib")            # calibrated, for predictions
    np.save("models/X_test.npy", X_test)
    np.save("models/y_test.npy", y_test)
    print("  Saved: models/risk_model.joblib (calibrated)")
    print("  Saved: models/risk_model_base.joblib (for SHAP)")
    print("  Saved: models/X_test.npy, models/y_test.npy")
    
    # Feature importance (model-internal)
    # CalibratedClassifierCV wraps the base model — access via .estimator
    importances = base_model.feature_importances_
    indices = np.argsort(importances)[::-1][:10]
    for rank, idx in enumerate(indices, 1):
        name = FEATURE_NAMES[idx] if idx < len(FEATURE_NAMES) else f"feature_{idx}"
        print(f"  {rank:2d}. {name:35s} importance={importances[idx]:.4f}")
    return model


if __name__ == "__main__":
    model = train()
    print("\n Training complete.")

