<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import type { FairnessReport } from '$lib/types';

  let report: FairnessReport | null = $state(null);
  let loading = $state(true);
  let error: string | null = $state(null);

  onMount(async () => {
    try {
      report = await api.fairnessReport();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load fairness report';
    } finally {
      loading = false;
    }
  });

  function formatPct(v: number): string {
    return `${(v * 100).toFixed(1)}%`;
  }

  function formatGroup(g: string): string {
    return g.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  }
</script>

<div class="mx-auto max-w-4xl px-6 py-12">
  <a href="/" class="inline-flex items-center text-sm text-text-muted hover:text-text mb-8">
    ← Back to patients
  </a>

  <header class="mb-8">
    <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-2">
      Fairness Audit
    </p>
    <h1 class="text-3xl font-semibold tracking-tight mb-2">Equalized Odds by Ethnicity</h1>
    <p class="text-text-muted text-sm">
      Per-group recall at the operating threshold. Computed offline against the full dataset.
    </p>
  </header>

  {#if loading}
    <p class="text-text-muted">Loading fairness report…</p>
  {:else if error}
    <div class="rounded-xl border border-error bg-error/10 p-5">
      <p class="text-error font-medium">Failed to load</p>
      <p class="text-sm text-text-muted mt-1">{error}</p>
    </div>
  {:else if report}
    <div class="space-y-6">
      <!-- Verdict card -->
<section class="rounded-2xl border border-border bg-surface p-6">
  <div class="flex items-baseline justify-between gap-4 mb-4">
    <div>
      <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-1">
        Decision metric
      </p>
      <p class="text-2xl font-semibold {report.verdict === 'PASS' ? 'text-reliable' : 'text-error'}">
        {report.verdict}
      </p>
      <p class="text-xs text-text-muted mt-1">Named-group equalized-odds gap</p>
    </div>
    <div class="text-right text-sm">
      <p class="text-text-muted mb-1">Gap</p>
      <p class="text-xl tabular-nums font-medium">
        {formatPct(report.named_group_gap)}
        <span class="text-xs text-text-subtle">/ {formatPct(report.gap_threshold)} threshold</span>
      </p>
    </div>
  </div>
  <div class="grid grid-cols-2 gap-4 pt-4 border-t border-border text-xs">
    <div>
      <p class="text-text-subtle mb-1">Full equalized-odds difference</p>
      <p class="tabular-nums text-text-muted">{formatPct(report.full_equalized_odds_difference)}</p>
    </div>
    <div>
      <p class="text-text-subtle mb-1">Auditor's overall flag</p>
      <p class="text-text-muted uppercase">{report.overall_flag}</p>
    </div>
  </div>
</section>

      <!-- Named groups -->
      <section class="rounded-2xl border border-border bg-surface p-6">
        <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-1">
          Named clinical groups
        </p>
        <p class="text-sm text-text-muted mb-5">
          Equalized-odds decision metric. Recall must be similar across these groups.
        </p>
        <ul class="space-y-3">
          {#each report.named_groups as g}
            <li>
              <div class="flex items-baseline justify-between mb-1">
                <span class="text-sm">{formatGroup(g.group)}</span>
                <span class="text-sm tabular-nums text-text-muted">
                  {formatPct(g.recall)} <span class="text-xs text-text-subtle">({g.n_total} positives)</span>
                </span>
              </div>
              <div class="h-1.5 rounded-full bg-surface-hover overflow-hidden">
                <div class="h-full bg-reliable" style="width: {g.recall * 100}%"></div>
              </div>
            </li>
          {/each}
        </ul>
      </section>

      <!-- Residual buckets -->
<section class="rounded-2xl border border-border bg-surface p-6">
  <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-1">
    Residual buckets
  </p>
  <p class="text-sm text-text-muted mb-5">
    Heterogeneous categories shown for transparency. Disparities here may be artifactual
    rather than clinical — these groups are mixed in composition.
  </p>
  <ul class="space-y-3">
    {#each report.residual_groups as g}
      <li>
        <div class="flex items-baseline justify-between mb-1">
          <span class="text-sm text-text-muted">{formatGroup(g.group)}</span>
          <span class="text-sm tabular-nums text-text-muted">
            {formatPct(g.recall)} <span class="text-xs text-text-subtle">(n={g.n_total})</span>
          </span>
        </div>
        <div class="h-1.5 rounded-full bg-surface-hover overflow-hidden">
          <div class="h-full bg-text-subtle" style="width: {g.recall * 100}%"></div>
        </div>
      </li>
    {/each}
  </ul>
</section>

<!-- Auditor's own notes -->
<section class="rounded-2xl border border-border bg-surface p-6">
  <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-1">
    Auditor's interpretation
  </p>
  <p class="text-sm text-text-muted mb-5">
    Notes written by the offline fairness auditor at computation time. Surfaced verbatim.
  </p>
  <ul class="space-y-3">
    {#each report.audit_notes as note}
      <li class="border-l-2 border-border pl-4 text-sm text-text-muted leading-relaxed">
        {note}
      </li>
    {/each}
  </ul>
</section>
    </div>
  {/if}
</div>