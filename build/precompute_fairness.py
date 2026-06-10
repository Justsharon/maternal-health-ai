"""
Sentinel — Precompute Fairness Report

Build-time script. Runs the fairness audit once and saves the report as
JSON for the dashboard to display. The fairness audit is offline by
design (Week 3 Day 1) — it's a system-level property, not a per-request
calculation. This script materializes the report.

Run whenever: model retrains, dataset changes, or fairness thresholds change.

Run with: PYTHONPATH=. python3 build/precompute_fairness.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import asdict

from agents.fairness_auditor import audit_fairness, RESIDUAL_GROUPS


OUTPUT_PATH = "data/fairness_report.json"
THRESHOLD = 0.1
GAP_THRESHOLD = 0.10  # named-group gap must be below this for PASS


def compute_report():
    print("Running fairness audit across the synthetic dataset...")
    report = audit_fairness(
        protected_attribute="ethnicity",
        threshold=THRESHOLD,
    )
    report_dict = asdict(report)

    # Separate named clinical groups from residual buckets
    named_tprs = {
        g: v for g, v in report.per_group_tpr.items()
        if g not in RESIDUAL_GROUPS
    }
    residual_tprs = {
        g: v for g, v in report.per_group_tpr.items()
        if g in RESIDUAL_GROUPS
    }

    named_gap = max(named_tprs.values()) - min(named_tprs.values())

    # PASS verdict: named-group gap below threshold (decision metric).
    # The audit's own 'flag' ('review' here) reflects the full-group gap
    # including residuals — surfaced separately as overall_flag below.
    verdict = "PASS" if named_gap < GAP_THRESHOLD else "FAIL"

    output = {
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "protected_attribute": report.protected_attribute,
        "operating_threshold": report.threshold,
        "gap_threshold": GAP_THRESHOLD,
        "named_groups": [
            {
                "group": g,
                "recall": report.per_group_tpr[g],
                "false_positive_rate": report.per_group_fpr[g],
                "n_total": report.per_group_n[g],
            }
            for g in sorted(named_tprs)
        ],
        "residual_groups": [
            {
                "group": g,
                "recall": report.per_group_tpr[g],
                "false_positive_rate": report.per_group_fpr[g],
                "n_total": report.per_group_n[g],
            }
            for g in sorted(residual_tprs)
        ],
        "named_group_gap": named_gap,
        "full_equalized_odds_difference": report.equalized_odds_difference,
        "demographic_parity_difference": report.demographic_parity_difference,
        "verdict": verdict,
        "overall_flag": report.flag,
        "audit_notes": report.notes,
    }
    return output


def save_report(report: dict, path: str = OUTPUT_PATH):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    size_kb = Path(path).stat().st_size / 1024
    print(f"\nFairness report saved to {path} ({size_kb:.1f} KB)")
    print(f"\nVerdict (named-group decision metric): {report['verdict']}")
    print(f"  Named-group gap: {report['named_group_gap']:.3f} (threshold {report['gap_threshold']})")
    print(f"  Full equalized-odds difference: {report['full_equalized_odds_difference']:.3f}")
    print(f"  Audit's own flag: {report['overall_flag']}")


if __name__ == "__main__":
    report = compute_report()
    save_report(report)