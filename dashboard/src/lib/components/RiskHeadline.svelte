<script lang="ts">
  import StatusBadge from './StatusBadge.svelte';
  import type { AssessmentResult } from '$lib/types';

  let { result }: { result: AssessmentResult } = $props();

  const riskPct = $derived(result.risk_probability != null
    ? `${(result.risk_probability * 100).toFixed(1)}%`
    : '—');
  const baselinePct = $derived(result.explanation
    ? `${(result.explanation.base_probability * 100).toFixed(1)}%`
    : '—');
</script>

<section class="rounded-3xl border border-border bg-surface p-10">
  <p class="text-[11px] font-medium uppercase tracking-[0.12em] text-text-subtle mb-6">
    Pre-eclampsia risk estimate
  </p>

  <div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-6 mb-8">
    <div>
      <div class="flex items-baseline gap-4">
        <span class="text-7xl font-semibold tracking-tight tabular-nums leading-none">
          {riskPct}
        </span>
        <span class="text-sm text-text-muted pb-2">
          vs {baselinePct} baseline
        </span>
      </div>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      {#if result.routing_decision === 'in_scope'}
        <StatusBadge variant="in-scope" label="In scope" />
      {:else if result.routing_decision === 'escalate'}
        <StatusBadge variant="escalate" label="Escalated to specialist" />
      {:else if result.routing_decision === 'out_of_scope'}
        <StatusBadge variant="out-of-scope" label="Out of scope" />
      {/if}
    </div>
  </div>

  <div class="flex flex-wrap items-center gap-4 pt-6 border-t border-border">
    {#if result.reliability_flag === 'reliable'}
      <StatusBadge variant="reliable" label="Reliable prediction" />
    {:else if result.reliability_flag === 'reduced_reliability'}
      <StatusBadge variant="reduced" label="Reduced reliability" />
    {/if}
    {#if result.confidence != null}
      <div class="text-sm text-text-muted">
        Model confidence
        <span class="text-text font-semibold tabular-nums ml-1">{result.confidence.toFixed(2)}</span>
      </div>
    {/if}
  </div>
</section>