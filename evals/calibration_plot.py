"""
Sentinel — Calibration Plot

Visual proof that the model's predicted probabilities track observed
frequencies. A calibrated model produces a reliability curve close to
the y=x diagonal — when it says 30% risk, ~30% of those patients
actually develop pre-eclampsia.

Generates two plots side-by-side:
  - Uncalibrated base model (what the raw XGBoost output looks like)
  - Calibrated model (after CalibratedClassifierCV isotonic fix)

The contrast is the demo evidence that the Week-1 calibration refactor
was necessary, not cosmetic.

Bucket count = 10 deciles, chosen because at 5000 patients and ~8.6%
incidence we have ~40 positives per decile — enough sample size that
deviation from diagonal reflects real miscalibration, not sampling noise.

Reference: Wong et al. (calibration as a deployment requirement),
the scale_pos_weight distortion documented on Week 1 Day 4.
"""

import numpy as np
import joblib
import matplotlib
matplotlib.use("Agg")  # non-interactive backend; works in any environment
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve
from sklearn.metrics import brier_score_loss

from data.generator import load_dataset
from models.feature_extractor import build_feature_matrix


N_BINS = 10  # 10 deciles; see header for rationale


def plot_calibration(output_path: str = "evals/calibration_plot.png"):
    """Generate side-by-side calibration plots for base vs calibrated model."""
    patients = load_dataset("synthetic_data.json")
    X, y = build_feature_matrix(patients)
    
    base_model = joblib.load("models/risk_model_base.joblib")
    calibrated_model = joblib.load("models/risk_model.joblib")
    
    base_proba = base_model.predict_proba(X)[:, 1]
    calibrated_proba = calibrated_model.predict_proba(X)[:, 1]
    # Match the user-facing cap from agents/risk_predictor.py — clinicians
    # never see raw 0.000 or 1.000 from this system, so the calibration plot
    # must reflect the predictions they would actually see, not raw model output.
    calibrated_proba = np.clip(calibrated_proba, 0.01, 0.95)
    
    # Per-bucket observed frequencies and mean predicted probabilities
    base_obs, base_pred = calibration_curve(y, base_proba, n_bins=N_BINS, strategy="quantile")
    cal_obs, cal_pred = calibration_curve(y, calibrated_proba, n_bins=N_BINS, strategy="quantile")
    
    # Brier score summary metric (lower is better)
    base_brier = brier_score_loss(y, base_proba)
    cal_brier = brier_score_loss(y, calibrated_proba)
    
    # Per-bin sample counts (so the demo can answer "is that noise or real?")
    base_bin_edges = np.quantile(base_proba, np.linspace(0, 1, N_BINS + 1))
    base_bin_counts = np.histogram(base_proba, bins=base_bin_edges)[0]
    cal_bin_edges = np.quantile(calibrated_proba, np.linspace(0, 1, N_BINS + 1))
    cal_bin_counts = np.histogram(calibrated_proba, bins=cal_bin_edges)[0]
    
    # --- Plot ---
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

    for ax, obs, pred, brier, title in [
        (axes[0], base_obs, base_pred, base_brier,
        f"Uncalibrated base model (Brier = {base_brier:.4f})"),
        (axes[1], cal_obs, cal_pred, cal_brier,
        f"Calibrated model (Brier = {cal_brier:.4f})"),
    ]:
        ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="Perfect calibration")
        ax.plot(pred, obs, "o-", linewidth=2, markersize=8, label="Model")
        ax.set_xlabel("Predicted probability (bin mean)")
        ax.set_ylabel("Observed frequency")
        ax.set_title(title)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.3)
        ax.legend(loc="upper left")

    # Third subplot: distribution of predicted probabilities (the discretization
    # made visible as evidence, not hidden). Shows WHERE the model commits.
    axes[2].hist(calibrated_proba, bins=40, edgecolor="black", alpha=0.75)
    axes[2].set_xlabel("Predicted probability")
    axes[2].set_ylabel("Number of patients")
    axes[2].set_title("Distribution of calibrated predictions\n"
                    "(after 0.01/0.95 display cap)")
    axes[2].set_xlim(0, 1)
    axes[2].grid(alpha=0.3, axis="y")

    plt.suptitle("Sentinel — Model calibration and prediction distribution",
             fontsize=14)
    plt.tight_layout()
    plt.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close()
    
    # --- Text report (for the demo, since plots alone don't tell the story) ---
    print(f"Calibration plot saved to {output_path}")
    print()
    print(f"Brier score (lower = better calibrated):")
    print(f"  Uncalibrated base model: {base_brier:.4f}")
    print(f"  Calibrated model:        {cal_brier:.4f}")
    print(f"  Improvement:             {(base_brier - cal_brier):.4f}")
    print()
    print(f"Per-bin sample sizes (calibrated model, 10 deciles):")
    print(f"  min={cal_bin_counts.min()}, max={cal_bin_counts.max()}, "
          f"mean={cal_bin_counts.mean():.0f}")
    print(f"  (samples-per-bin >> 20 needed for stable observed frequencies)")
    print()
    print("Calibrated model: predicted vs observed by bin")
    print(f"{'Predicted':>10} {'Observed':>10} {'Gap':>8}")
    for p, o in zip(cal_pred, cal_obs):
        print(f"  {p:>8.3f}    {o:>8.3f}    {(o-p):>+6.3f}")


if __name__ == "__main__":
    plot_calibration()