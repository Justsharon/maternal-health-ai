"""
Sentinel — Fairness Auditor (Agent 7)

ARCHITECTURE NOTE: This is a BATCH agent, not a per-request agent. Fairness
is an aggregate population property — a single prediction cannot be "fair".
It therefore runs OFFLINE over a batch of predictions (the gold set or the
audit log), NOT inside the per-request LangGraph orchestrator.

FAIRNESS PHILOSOPHY (established in design):
  - Equalized Odds is the DECISION metric (conditions on true outcome;
    fair regardless of differing base rates across groups).
  - Demographic Parity is reported as CONTEXT only (our groups have
    genuinely different true incidence, so unequal flagging is correct,
    not biased — forcing parity would underserve the highest-risk group).
  - Named clinical groups are distinguished from residual buckets
    ("other", "not_disclosed"), which are heterogeneous and may show
    artifactual disparities.
  - Fairness is threshold-dependent; the evaluated threshold is reported.

Reference: Dwork (group-fairness vs accuracy tradeoff), WHO Principle 5
(inclusiveness — you can only audit the groups your data resolves).
"""

import numpy as np
import joblib
from dataclasses import dataclass, field

from fairlearn.metrics import (
    MetricFrame,
    true_positive_rate,
    false_positive_rate,
    selection_rate,
    demographic_parity_difference,
    equalized_odds_difference,
)

from data.generator import load_dataset
from models.feature_extractor import build_feature_matrix


# Groups that are heterogeneous residual buckets, not coherent clinical
# populations. Disparities here need careful interpretation.
RESIDUAL_GROUPS = {"other", "not_disclosed"}

# Decision threshold for flagging a fairness concern on equalized odds.
# 0.10 = a 10-percentage-point recall gap between groups is the action line.
EQUALIZED_ODDS_FLAG_THRESHOLD = 0.10


@dataclass
class FairnessReport:
    threshold: float
    protected_attribute: str
    per_group_tpr: dict
    per_group_fpr: dict
    per_group_selection_rate: dict
    per_group_n: dict
    equalized_odds_difference: float
    demographic_parity_difference: float
    flag: str                       # "pass" | "review" | "concern"
    notes: list = field(default_factory=list)


def audit_fairness(
    protected_attribute: str = "ethnicity",
    threshold: float = 0.1,
) -> FairnessReport:
    """
    Run a fairness audit over the full synthetic dataset.

    Big-O: O(N) for prediction + O(N) for metric aggregation = O(N).
    At N=5000 this is milliseconds. At production scale (millions of
    logged predictions) you'd batch/sample — noted in production verdict.
    Memory: O(N) for the prediction arrays + O(G) for per-group stats.
    """
    patients = load_dataset("synthetic_data.json")
    model = joblib.load("models/risk_model.joblib")

    X, y_true = build_feature_matrix(patients)
    y_proba = model.predict_proba(X)[:, 1]
    y_pred = (y_proba >= threshold).astype(int)

    # Extract the protected attribute per patient
    sensitive = np.array([
        getattr(p, protected_attribute).value
        if hasattr(getattr(p, protected_attribute), "value")
        else getattr(p, protected_attribute)
        for p in patients
    ])

    # --- Fairlearn MetricFrame: per-group metrics in one pass ---
    metric_frame = MetricFrame(
        metrics={
            "tpr": true_positive_rate,
            "fpr": false_positive_rate,
            "selection_rate": selection_rate,
        },
        y_true=y_true,
        y_pred=y_pred,
        sensitive_features=sensitive,
    )

    per_group = metric_frame.by_group
    per_group_tpr = per_group["tpr"].to_dict()
    per_group_fpr = per_group["fpr"].to_dict()
    per_group_sel = per_group["selection_rate"].to_dict()
    per_group_n = {
        g: int(np.sum(sensitive == g)) for g in per_group_tpr.keys()
    }

    # --- The two aggregate metrics ---
    eo_diff = float(equalized_odds_difference(
        y_true, y_pred, sensitive_features=sensitive
    ))
    dp_diff = float(demographic_parity_difference(
        y_true, y_pred, sensitive_features=sensitive
    ))

    # --- Decision logic: flag on EQUALIZED ODDS, interpret residual groups ---
    notes = []
    report = FairnessReport(
        threshold=threshold,
        protected_attribute=protected_attribute,
        per_group_tpr=per_group_tpr,
        per_group_fpr=per_group_fpr,
        per_group_selection_rate=per_group_sel,
        per_group_n=per_group_n,
        equalized_odds_difference=eo_diff,
        demographic_parity_difference=dp_diff,
        flag="pass",
        notes=notes,
    )

    # Identify worst-served group on recall
    worst_group = min(per_group_tpr, key=per_group_tpr.get)
    best_group = max(per_group_tpr, key=per_group_tpr.get)

    # Recompute the gap among NAMED (non-residual) groups only
    named_tpr = {g: v for g, v in per_group_tpr.items()
                 if g not in RESIDUAL_GROUPS}
    named_gap = (max(named_tpr.values()) - min(named_tpr.values())
                 if named_tpr else 0.0)

    if eo_diff < EQUALIZED_ODDS_FLAG_THRESHOLD:
        report.flag = "pass"
        notes.append(
            f"Equalized odds difference {eo_diff:.3f} is below the "
            f"{EQUALIZED_ODDS_FLAG_THRESHOLD} action threshold."
        )
    else:
        # Disparity exists — is it driven by residual buckets or named groups?
        if worst_group in RESIDUAL_GROUPS and named_gap < EQUALIZED_ODDS_FLAG_THRESHOLD:
            report.flag = "review"
            notes.append(
                f"Equalized odds difference {eo_diff:.3f} EXCEEDS threshold, "
                f"but the disparity is driven by the residual group "
                f"'{worst_group}' (recall {per_group_tpr[worst_group]:.3f}). "
                f"Among named clinical groups the recall gap is only "
                f"{named_gap:.3f} (within threshold)."
            )
            notes.append(
                "INTERPRETATION: residual groups ('other', 'not_disclosed') "
                "are heterogeneous and may show artifactual disparities. This "
                "cannot be distinguished from a real subgroup concern without "
                "finer-grained data. RECOMMENDATION: collect granular ethnicity "
                "data in production; document reduced validation for these buckets."
            )
        else:
            report.flag = "concern"
            notes.append(
                f"Equalized odds difference {eo_diff:.3f} EXCEEDS threshold and "
                f"the worst-served group '{worst_group}' "
                f"(recall {per_group_tpr[worst_group]:.3f}) is a NAMED clinical "
                f"group. This is a genuine fairness concern requiring model "
                f"investigation before deployment."
            )

    # Always note the highest-risk groups' standing (the ones that matter most)
    notes.append(
        f"Best-served: {best_group} ({per_group_tpr[best_group]:.3f}); "
        f"worst-served: {worst_group} ({per_group_tpr[worst_group]:.3f})."
    )
    notes.append(
        f"Demographic parity difference {dp_diff:.3f} reported as CONTEXT "
        f"only — groups have genuinely different true incidence, so unequal "
        f"flagging reflects real risk, not bias. Decision metric is "
        f"equalized odds."
    )

    return report


def print_report(report: FairnessReport):
    print("=" * 72)
    print(f"FAIRNESS AUDIT — protected attribute: {report.protected_attribute}")
    print(f"Evaluated at threshold: {report.threshold}")
    print("=" * 72)
    print(f"{'Group':<18} {'n':>5} {'recall(TPR)':>12} {'FPR':>8} {'flag_rate':>10}")
    print("-" * 72)
    for g in sorted(report.per_group_tpr.keys()):
        marker = " *" if g in RESIDUAL_GROUPS else ""
        print(f"{g:<18} {report.per_group_n[g]:>5} "
              f"{report.per_group_tpr[g]:>12.3f} "
              f"{report.per_group_fpr[g]:>8.3f} "
              f"{report.per_group_selection_rate[g]:>10.3f}{marker}")
    print("-" * 72)
    print("  * = residual bucket (heterogeneous; interpret disparities with care)")
    print()
    print(f"DECISION METRIC — Equalized Odds Difference: "
          f"{report.equalized_odds_difference:.3f}")
    print(f"CONTEXT ONLY    — Demographic Parity Difference: "
          f"{report.demographic_parity_difference:.3f}")
    print()
    print(f"FLAG: {report.flag.upper()}")
    print()
    print("Notes:")
    for n in report.notes:
        print(f"  • {n}")


if __name__ == "__main__":
    report = audit_fairness(protected_attribute="ethnicity", threshold=0.1)
    print_report(report)