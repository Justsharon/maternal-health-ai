<script lang="ts">
  import type { Explanation } from '$lib/types';

  let { explanation }: { explanation: Explanation } = $props();

  // Filter to contributions that meaningfully moved the estimate
  const significant = $derived(explanation.top_contributions.filter(
    (c) => Math.abs(c.shap_value) > 0.01
  ));
  // Maximum absolute value, for proportional bar widths
  const maxAbs = $derived(Math.max(...significant.map((c) => Math.abs(c.shap_value)), 0.01));
</script>

<section class="rounded-3xl border border-border bg-surface overflow-hidden">
  <div class="grid grid-cols-1 lg:grid-cols-5 gap-0">
    <!-- LEFT: the narrative -->
`   <div class="p-6">
    <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-3">
        Plain-language explanation
    </p>
    {#if explanation.narrative.includes('[NO_RECORDING_AVAILABLE]')}
        <div class="rounded-md border border-reduced/30 bg-reduced/5 p-4">
        <p class="text-sm text-reduced font-medium mb-1">Live explanation not available</p>
        <p class="text-xs text-text-muted leading-relaxed">
            This deployment runs in deterministic mock mode for the pre-recorded demo
            patients. Custom patients require the live LLM mode, which is enabled in
            production deployments with a Groq API key configured.
        </p>
        <p class="text-xs text-text-subtle mt-2">
            The feature contributions on the right are still computed in real time
            and show the model's actual reasoning.
        </p>
        </div>
    {:else}
        <p class="text-sm leading-relaxed whitespace-pre-line">
        {explanation.narrative}
        </p>
    {/if}
    </div>`

    <!-- RIGHT: contributions (40% on desktop) -->
    <div class="lg:col-span-2 p-10 border-t lg:border-t-0 border-border">
      <p class="text-[11px] font-medium uppercase tracking-[0.12em] text-text-subtle mb-5">
        Feature contributions
      </p>

      <ul class="space-y-5">
        {#each significant as c}
          {@const isPositive = c.shap_value >= 0}
          {@const widthPct = Math.max(8, (Math.abs(c.shap_value) / maxAbs) * 100)}
          <li>
            <div class="flex items-baseline justify-between gap-3 mb-2">
              <span class="text-[13px] text-text font-medium leading-snug">
                {c.label}
              </span>
              <span class="text-[11px] text-text-subtle shrink-0 tabular-nums">
                {isPositive ? '+' : '−'}{Math.abs(c.shap_value).toFixed(3)}
              </span>
            </div>
            <div class="h-2 rounded-full bg-bg overflow-hidden">
              <div
                class="h-full rounded-full {isPositive ? 'bg-escalate' : 'bg-reliable'}"
                style="width: {widthPct}%"
              ></div>
            </div>
            <p class="text-[11px] text-text-muted mt-1.5">
              {isPositive ? 'Increased' : 'Decreased'} the estimate
            </p>
          </li>
        {/each}
      </ul>

      <p class="text-[11px] leading-relaxed text-text-subtle mt-8 pt-5 border-t border-border">
        The narrative on the left describes only these contributions. Any claim not traceable to this list would be flagged by the Clinical Reviewer agent.
      </p>
    </div>
  </div>
</section>