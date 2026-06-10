<script lang="ts">
  import StatusBadge from './StatusBadge.svelte';
  import type { AssessmentResult } from '$lib/types';

  let { result }: { result: AssessmentResult } = $props();
</script>

<section class="rounded-3xl border border-border bg-surface px-10 py-6">
  <div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
    <div class="flex flex-col md:flex-row md:items-center gap-3 md:gap-5">
        {#if result.review_status === 'approved'}
            <StatusBadge variant="approved" label="Reviewer: approved" />
        {:else if result.review_status === 'needs_review'}
            <StatusBadge variant="needs-review" label="Reviewer: needs human review" />
        {:else if result.review_status === 'no_explanation'}
            <StatusBadge variant="reduced" label="Reviewer: skipped — no explanation" />
        {/if}

        {#if result.review_notes}
            <span class="text-text-muted text-[13px] leading-snug max-w-xl">
            {result.review_notes}
            </span>
        {/if}
    </div>

    {#if result.audit_id}
      <div class="text-[11px] text-text-subtle font-mono whitespace-nowrap">
        AUDIT {result.audit_id.slice(0, 8)}
      </div>
    {/if}
  </div>
</section>