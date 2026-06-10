<script lang="ts">
  import type { Guideline } from '$lib/types';

  let { guidelines }: { guidelines: Guideline[] } = $props();
</script>

<section class="rounded-3xl border border-border bg-surface p-10">
  <p class="text-[11px] font-medium uppercase tracking-[0.12em] text-text-subtle mb-2">
    Related clinical guidance
  </p>
  <p class="text-sm text-text-muted mb-8 max-w-2xl">
    For the factors considered in this assessment — not endorsement of the model's specific estimate.
  </p>

  {#if guidelines.length === 0}
    <p class="text-sm text-text-subtle">
      No directly related guidance found for this patient's risk factors.
    </p>
  {:else}
    <ul class="space-y-6">
      {#each guidelines as g}
        <li class="border-l-2 border-approved/40 pl-5">
          <p class="text-[11px] font-semibold text-approved uppercase tracking-wider mb-2">
            {g.source}
          </p>
          <p class="text-[14px] leading-relaxed text-text">{g.summary}</p>
        </li>
      {/each}
    </ul>
  {/if}

  <p class="text-[11px] text-text-subtle mt-8 pt-5 border-t border-border leading-relaxed max-w-2xl">
    This guidance relates to the clinical factors in this assessment. It does not validate the model's specific risk estimate. Clinical correlation and judgment are required.
  </p>
</section>