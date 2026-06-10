<script lang="ts">
  import { page } from '$app/state';
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import type { AssessmentResult } from '$lib/types';

  import RiskHeadline from '$lib/components/RiskHeadline.svelte';
  import ReliabilityBanner from '$lib/components/ReliabilityBanner.svelte';
  import NarrativeAndShap from '$lib/components/NarrativeAndShap.svelte';
  import GuidanceSection from '$lib/components/GuidanceSection.svelte';
  import AuditFooter from '$lib/components/AuditFooter.svelte';

  let result: AssessmentResult | null = $state(null);
  let loading = $state(true);
  let error: string | null = $state(null);

  onMount(async () => {
    const patientId = page.params.id;
    try {
      result = await api.assessDemo(patientId!);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load assessment';
    } finally {
      loading = false;
    }
  });
</script>

<div class="mx-auto max-w-6xl px-6 py-16">
  <a href="/" class="inline-flex items-center text-sm text-text-muted hover:text-text mb-12 transition-colors">
    ← Back to patients
  </a>

  {#if loading}
    <p class="text-text-muted">Running assessment through the 9-agent pipeline…</p>
  {:else if error}
    <div class="rounded-3xl border border-error bg-error/10 p-8">
      <p class="text-error font-semibold mb-2">Assessment failed</p>
      <p class="text-sm text-text-muted">{error}</p>
    </div>
  {:else if result}
    {#if !result.privacy_passed}
      <div class="rounded-3xl border border-error bg-error/10 p-8">
        <p class="text-error font-semibold mb-2">Record rejected at privacy gate</p>
        <p class="text-sm text-text-muted">{result.privacy_notes}</p>
      </div>
    {:else}
      <div class="space-y-8">
        <RiskHeadline {result} />

        {#if result.reliability_flag === 'reduced_reliability' && result.reliability_reason}
          <ReliabilityBanner reason={result.reliability_reason} />
        {/if}

        {#if result.explanation}
          <NarrativeAndShap explanation={result.explanation} />
        {/if}

        {#if result.relevant_guidelines}
          <GuidanceSection guidelines={result.relevant_guidelines} />
        {/if}

        <AuditFooter {result} />
      </div>
    {/if}
  {/if}
</div>