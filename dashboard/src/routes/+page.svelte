<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import type { DemoPatientSummary } from '$lib/types';

  let patients: DemoPatientSummary[] = $state([]);
  let loading = $state(true);
  let error: string | null = $state(null);

  onMount(async () => {
    try {
      patients = await api.listDemoPatients();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load patients';
    } finally {
      loading = false;
    }
  });
</script>

<div class="mx-auto max-w-5xl px-6 py-16">
  <header class="mb-12">
    <p class="text-sm font-medium text-sky-400/80 mb-2">
      Maternal Health Risk Insight
    </p>
    <h1 class="text-4xl font-semibold tracking-tight mb-3">Sentinel</h1>
    <p class="text-slate-400 max-w-2xl">
      A 9-agent clinical AI pipeline for pre-eclampsia risk prediction.
      Select a demo patient to walk through the full assessment.
    </p>
  </header>

  {#if loading}
    <p class="text-slate-400">Loading patients…</p>
  {:else if error}
    <div class="rounded-lg border border-error bg-error/10 p-4">
      <p class="text-error font-medium">API error</p>
      <p class="text-sm text-slate-400 mt-1">{error}</p>
      <p class="text-xs text-slate-500 mt-3">
        Make sure the FastAPI backend is running: <code>uvicorn api.main:app --port 8000</code>
      </p>
    </div>
  {:else}
    <div class="grid gap-4 sm:grid-cols-2">
      {#each patients as patient}
        <a
          href="/patient/{patient.patient_id}"
          class="block rounded-xl border border-slate-700 bg-slate-900
                 hover:bg-slate-900-hover hover:border-slate-400
                 transition-colors p-6"
        >
          <div class="flex items-baseline justify-between mb-3">
            <h2 class="font-semibold">{patient.patient_id}</h2>
            <span class="text-xs text-slate-500">
              Week {patient.current_gestational_week}
            </span>
          </div>
          <dl class="grid grid-cols-2 gap-y-1 text-sm text-slate-400">
            <dt>Age</dt><dd class="text-text">{patient.age}</dd>
            <dt>Ethnicity</dt><dd class="text-text">{patient.ethnicity}</dd>
            <dt>BMI</dt><dd class="text-text">{patient.bmi_at_booking}</dd>
          </dl>
          <p class="text-xs mt-4 text-slate-500">
            Expected: {patient.expected_routing}
          </p>
        </a>
      {/each}
    </div>
  {/if}

  <div class="mt-8 rounded-2xl border border-slate-700 border-dashed bg-slate-900/50 p-6 text-center">
    <p class="text-sm font-medium mb-1">Or enter a custom patient</p>
    <p class="text-xs text-slate-400 mb-4">
      Synthetic demo data only. Validated against the same schema as the demo patients.
    </p>
    <a href="/new"
      class="inline-block px-4 py-2 text-sm font-medium rounded-md bg-sky-400/15 text-sky-400
              border border-sky-400/30 hover:bg-sky-400/25 transition-colors">
      + New patient assessment
    </a>
  </div>

  <nav class="mt-12 pt-8 border-t border-slate-700">
  <p class="text-xs font-medium uppercase tracking-wider text-slate-500 mb-4">
    System views
  </p>
  <div class="grid gap-3 sm:grid-cols-2">
    <a
      href="/audit"
      class="block rounded-xl border border-slate-700 bg-slate-900
             hover:bg-slate-900-hover hover:border-slate-400 transition-colors p-5"
    >
      <p class="font-medium mb-1">Audit Log</p>
      <p class="text-sm text-slate-400">
        Every prediction the system has made, append-only.
      </p>
    </a>
    <a
      href="/fairness"
      class="block rounded-xl border border-slate-700 bg-slate-900 hover:bg-slate-900-hover hover:border-slate-400 transition-colors p-5"
    >
      <p class="font-medium mb-1">Fairness Audit</p>
      <p class="text-sm text-slate-400">
        Per-group recall across ethnicities, named vs residual.
      </p>
    </a>
    <a href="/calibration" class="block rounded-xl border border-slate-700 bg-slate-900 hover:bg-slate-900-hover hover:border-slate-400 transition-colors p-5">
      <p class="font-medium mb-1">Calibration</p>
      <p class="text-sm text-slate-400">Reliability diagram and Brier score evidence.</p>
    </a>
  </div>
</nav>
</div>