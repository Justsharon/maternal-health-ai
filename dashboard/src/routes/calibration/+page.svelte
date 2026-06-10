<script lang="ts">
  // Static page — no backend call needed, the calibration plot is a pre-computed artifact
</script>

<div class="mx-auto max-w-4xl px-6 py-12">
  <a href="/" class="inline-flex items-center text-sm text-text-muted hover:text-text mb-8">
    ← Back to patients
  </a>

  <header class="mb-8">
    <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-2">
      Model Evidence
    </p>
    <h1 class="text-3xl font-semibold tracking-tight mb-2">Calibration</h1>
    <p class="text-text-muted text-sm leading-relaxed max-w-2xl">
      A reliability diagram asks one question: when the model says "30% risk," do 30% of those
      patients actually develop pre-eclampsia? A calibrated model produces a line close to the
      y=x diagonal. The Brier score is the standard summary metric — lower is better.
    </p>
  </header>

  <section class="rounded-2xl border border-border bg-surface overflow-hidden mb-6">
    <img src="/evidence/calibration.png" alt="Calibration plot: uncalibrated base model, calibrated model, and distribution of predictions"
         class="w-full h-auto block" />
  </section>

  <div class="space-y-4">
    <section class="rounded-2xl border border-border bg-surface p-6">
      <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-3">
        The story
      </p>
      <p class="text-sm leading-relaxed text-text-muted">
        The base XGBoost model was trained with <code class="text-text font-mono text-xs">scale_pos_weight</code>
        set to address class imbalance (8.6% incidence). This produced a strong-ranking model — but distorted
        probabilities. The model's confidence values clustered between 0.3 and 0.7, which is calibration failure:
        a "32% prediction" was no more reliable than a "65% prediction."
      </p>
      <p class="text-sm leading-relaxed text-text-muted mt-3">
        Isotonic calibration (sklearn's <code class="text-text font-mono text-xs">CalibratedClassifierCV</code>)
        was applied on a held-out calibration set. The Brier score dropped from <span class="text-text tabular-nums">0.148</span>
        to <span class="text-text tabular-nums">0.023</span> — an 84% reduction in calibration error.
        At each predicted probability the model now produces, observed frequency matches within 3-4
        percentage points.
      </p>
    </section>

    <section class="rounded-2xl border border-border bg-surface p-6">
      <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-3">
        Honest caveats
      </p>
      <p class="text-sm leading-relaxed text-text-muted">
        Isotonic regression is a step function. The calibrated model produces about 27 distinct probability
        values across 5000 patients — 53% of patients receive the model's lowest value (capped at 0.01 for
        display), about 24% receive the next-lowest (~0.04), with a high-risk tail at 0.7-0.95. The model
        is decisive: most patients route confidently low, a smaller group confidently high, and the uncertain
        middle is sparse.
      </p>
      <p class="text-sm leading-relaxed text-text-muted mt-3">
        For clinical decision support this is a feature, not a bug: low-confidence predictions correctly route
        to escalation rather than presenting an ambiguous number to the clinician. The plot reflects the
        user-facing display cap of 0.01-0.95, because no responsible clinical tool tells a clinician
        "0% risk" or "100% risk." Calibration evidence and clinical display behavior agree.
      </p>
    </section>

    <section class="rounded-2xl border border-border bg-surface p-6">
      <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-3">
        Why a held-out gold set, not the training data
      </p>
      <p class="text-sm leading-relaxed text-text-muted">
        The regression suite validates recall on a 100-patient gold set — stratified, held out from training,
        deliberately spanning edge cases. Performance on training data tells us nothing about generalization
        (the model already saw it). The Wong et al. sepsis study made this lesson permanent for clinical AI:
        internal validation is not external validity. The gold set is the proxy for external validity that
        every code change runs against.
      </p>
    </section>
  </div>
</div>