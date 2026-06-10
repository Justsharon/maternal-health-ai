<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import type { AssessmentResult } from '$lib/types';

  import RiskHeadline from '$lib/components/RiskHeadline.svelte';
  import ReliabilityBanner from '$lib/components/ReliabilityBanner.svelte';
  import NarrativeAndShap from '$lib/components/NarrativeAndShap.svelte';
  import GuidanceSection from '$lib/components/GuidanceSection.svelte';
  import AuditFooter from '$lib/components/AuditFooter.svelte';

  let result: AssessmentResult | null = $state(null);

  onMount(() => {
    const cached = sessionStorage.getItem('lastAssessment');
    if (!cached) {
      goto('/new');
      return;
    }
    result = JSON.parse(cached);
  });
</script>

<div class="mx-auto max-w-4xl px-6 py-12">
  <div class="flex items-baseline justify-between mb-8">
    <a href="/new" class="inline-flex items-center text-sm text-text-muted hover:text-text">
      ← Submit another patient
    </a>
    <a href="/" class="text-sm text-text-muted hover:text-text">All patients</a>
  </div>

  {#if result}
    <header class="mb-6">
      <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-2">
        Custom assessment result
      </p>
      <h1 class="text-2xl font-semibold tracking-tight">
        {result.validated_record?.patient_id ?? 'New patient'}
      </h1>
    </header>

    {#if !result.privacy_passed}
      <div class="rounded-xl border border-error bg-error/10 p-5">
        <p class="text-error font-medium mb-1">Record rejected at privacy gate</p>
        <p class="text-sm text-text-muted">{result.privacy_notes}</p>
      </div>
    {:else}
      <div class="space-y-5">
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