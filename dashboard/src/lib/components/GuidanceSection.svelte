<script lang="ts">
  import type { Guideline } from '$lib/types';

  let { guidelines }: { guidelines: Guideline[] } = $props();
</script>

<section class="rounded-3xl border border-slate-900 bg-slate-900 p-10">
  <p class="text-[11px] font-medium uppercase tracking-[0.12em] text-slate-500 mb-2">
    Related clinical guidance
  </p>
  <p class="text-sm text-slate-400 mb-8 max-w-2xl">
    For the factors considered in this assessment — not endorsement of the model's specific estimate.
  </p>

  {#if guidelines.length === 0}
    <p class="text-sm text-slate-500">
      No directly related guidance found for this patient's risk factors.
    </p>
  {:else}
    <ul class="space-y-6">
      {#each guidelines as g}
        <li class="border-l-2 border-sky-400/40 pl-5">
          <p class="text-[11px] font-semibold text-sky-400 uppercase tracking-wider mb-2">
            {g.source}
          </p>
          <p class="text-[14px] leading-relaxed text-text">{g.summary}</p>
        </li>
      {/each}
    </ul>
  {/if}

  <p class="text-[11px] text-slate-500 mt-8 pt-5 border-t border-slate-700 leading-relaxed max-w-2xl">
    This guidance relates to the clinical factors in this assessment. It does not validate the model's specific risk estimate. Clinical correlation and judgment are required.
  </p>
</section>