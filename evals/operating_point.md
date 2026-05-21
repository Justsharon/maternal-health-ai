# Sentinel Operating Point Decision

## Threshold: 0.1

## Rationale

Based on gold set threshold sweep (100 cases, 50 positive / 50 negative):

| Threshold | Recall | Precision | Missed | False Alarms |
|-----------|--------|-----------|--------|--------------|
| 0.1       | 0.88   | 0.92      | 6      | 4            |
| 0.2-0.5   | 0.80   | 0.98      | 10     | 1            |
| 0.7       | 0.78   | 0.98      | 11     | 1            |

We select **threshold 0.1** because:

1. **Asymmetric cost structure** — In maternal health, a missed pre-eclampsia
   case carries far greater harm (potential maternal/fetal death) than a false
   alarm (additional monitoring). This justifies optimising for recall.

2. **The 6 remaining missed cases are not a threshold problem** — All are
   early-pregnancy patients (gestational weeks 12-16) where the primary
   predictive signal (rising BP trajectory) has not yet emerged. No threshold
   would catch these without the underlying clinical signal.

## Documented Limitation

Sentinel's predictive reliability is concentrated in the 20+ week gestational
window. Predictions before week 18-20 have reduced reliability because BP
trajectory data is limited. The Confidence Calibrator (Agent 3) flags this
explicitly. Early-pregnancy patients should receive standard risk-factor
screening regardless of Sentinel's output.

## What This Threshold Does NOT Solve

- Cannot predict pre-eclampsia before warning signs emerge
- Cannot replace clinical judgment
- Requires clinician confirmation before any action