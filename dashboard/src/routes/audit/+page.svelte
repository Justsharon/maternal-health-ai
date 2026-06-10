<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import type { AuditEntry } from '$lib/types';
  import StatusBadge from '$lib/components/StatusBadge.svelte';

  let entries: AuditEntry[] = $state([]);
  let loading = $state(true);
  let error: string | null = $state(null);

  onMount(async () => {
    try {
      entries = await api.auditLog(50);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load audit log';
    } finally {
      loading = false;
    }
  });

  function formatTime(iso: string): string {
    return new Date(iso).toLocaleString();
  }

  function formatProb(p: number | null): string {
    return p == null ? '—' : `${(p * 100).toFixed(1)}%`;
  }
</script>

<div class="mx-auto max-w-5xl px-6 py-12">
  <a href="/" class="inline-flex items-center text-sm text-text-muted hover:text-text mb-8">
    ← Back to patients
  </a>

  <header class="mb-8">
    <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-2">
      Accountability
    </p>
    <h1 class="text-3xl font-semibold tracking-tight mb-2">Audit Log</h1>
    <p class="text-text-muted text-sm">
      Immutable record of every prediction the system has made. Append-only by design.
    </p>
  </header>

  {#if loading}
    <p class="text-text-muted">Loading audit entries…</p>
  {:else if error}
    <div class="rounded-xl border border-error bg-error/10 p-5">
      <p class="text-error font-medium">Failed to load</p>
      <p class="text-sm text-text-muted mt-1">{error}</p>
    </div>
  {:else if entries.length === 0}
    <p class="text-text-muted">No audit entries yet. Make an assessment to populate the log.</p>
  {:else}
    <div class="rounded-xl border border-border overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-surface text-xs font-medium uppercase tracking-wider text-text-subtle">
          <tr>
            <th class="text-left px-4 py-3">Time</th>
            <th class="text-left px-4 py-3">Patient</th>
            <th class="text-left px-4 py-3">Risk</th>
            <th class="text-left px-4 py-3">Routing</th>
            <th class="text-left px-4 py-3">Review</th>
          </tr>
        </thead>
        <tbody>
          {#each entries as e (e.entry_id)}
            <tr class="border-t border-border hover:bg-surface transition-colors">
              <td class="px-4 py-3 text-text-muted whitespace-nowrap">{formatTime(e.timestamp_utc)}</td>
              <td class="px-4 py-3">
                {#if e.patient_id}
                  <a href="/patient/{e.patient_id}" class="text-approved hover:underline font-mono text-xs">{e.patient_id}</a>
                {:else}
                  <span class="text-text-subtle text-xs italic">rejected at gate</span>
                {/if}
              </td>
              <td class="px-4 py-3 tabular-nums">{formatProb(e.risk_probability)}</td>
              <td class="px-4 py-3">
                {#if e.routing_decision === 'in_scope'}
                  <StatusBadge variant="in-scope" label="In scope" />
                {:else if e.routing_decision === 'escalate'}
                  <StatusBadge variant="escalate" label="Escalate" />
                {:else}
                  <span class="text-text-subtle text-xs">—</span>
                {/if}
              </td>
              <td class="px-4 py-3">
                {#if e.review_status === 'approved'}
                  <StatusBadge variant="approved" label="Approved" />
                {:else if e.review_status === 'needs_review'}
                  <StatusBadge variant="needs-review" label="Needs review" />
                {:else}
                  <span class="text-text-subtle text-xs">—</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>

    <p class="text-xs text-text-subtle mt-4 leading-relaxed">
      Showing {entries.length} most recent entries. Storage: SQLite with WAL mode, append-only by API design.
    </p>
  {/if}
</div>