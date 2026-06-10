<script lang="ts">
  import { goto } from '$app/navigation';
  import { api } from '$lib/api';

  // Form state
  let age = $state(30);
  let ethnicity = $state('white');
  let socioeconomic_proxy = $state('middle');
  let parity = $state(0);
  let multiple_pregnancy = $state(false);
  let current_gestational_week = $state(28);
  let pre_existing_hypertension = $state(false);
  let diabetes = $state('none');
  let prior_preeclampsia = $state(false);
  let family_history_preeclampsia = $state(false);
  let bmi_at_booking = $state(25.0);
  let proteinuria_level = $state<number | null>(null);

  // Symptoms — four booleans, default false
  let headache = $state(false);
  let visual_disturbance = $state(false);
  let epigastric_pain = $state(false);
  let swelling = $state(false);

  // BP readings — array of three rows by default
  type BPReading = { gestational_week: number; systolic: number; diastolic: number };
  let bp_readings: BPReading[] = $state([
    { gestational_week: 12, systolic: 118, diastolic: 75 },
    { gestational_week: 20, systolic: 122, diastolic: 78 },
    { gestational_week: 28, systolic: 124, diastolic: 80 },
  ]);

  let submitting = $state(false);
  let error: string | null = $state(null);

  function addReading() {
    const last = bp_readings[bp_readings.length - 1];
    bp_readings = [...bp_readings, {
      gestational_week: Math.min((last?.gestational_week ?? 12) + 4, 40),
      systolic: last?.systolic ?? 120,
      diastolic: last?.diastolic ?? 75,
    }];
  }
  function removeReading(i: number) {
    bp_readings = bp_readings.filter((_, idx) => idx !== i);
  }

  async function submit() {
    error = null;
    submitting = true;

    // Build the patient record — synthetic-only locked at the UI
    const patient = {
      patient_id: `USER-${Math.random().toString(36).slice(2, 10).toUpperCase()}`,
      is_synthetic: true,
      age,
      ethnicity,
      socioeconomic_proxy,
      parity,
      multiple_pregnancy,
      current_gestational_week,
      pre_existing_hypertension,
      diabetes,
      prior_preeclampsia,
      family_history_preeclampsia,
      bmi_at_booking,
      blood_pressure_readings: bp_readings,
      proteinuria_level,
      current_symptoms: { headache, visual_disturbance, epigastric_pain, swelling },
    };

    try {
      const result = await api.assess(patient);
      // Navigate to a result view. For a freshly-created patient we don't
      // have a /patient/[id] cache hit, so we'll stash the result in
      // session storage and navigate to /new/result.
      sessionStorage.setItem('lastAssessment', JSON.stringify(result));
      await goto('/new/result');
    } catch (e) {
      error = e instanceof Error ? e.message : 'Submission failed';
      submitting = false;
    }
  }
</script>

<div class="mx-auto max-w-3xl px-6 py-12">
  <a href="/" class="inline-flex items-center text-sm text-text-muted hover:text-text mb-8">
    ← Back to patients
  </a>

  <header class="mb-8">
    <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-2">
      Interactive
    </p>
    <h1 class="text-3xl font-semibold tracking-tight mb-2">New Patient Assessment</h1>
    <p class="text-text-muted text-sm">
      Enter synthetic patient data to run through the full nine-agent pipeline.
      All fields validate against the same Pydantic schema the privacy gate uses.
    </p>
    <p class="text-xs text-reduced mt-3">
      ⚠️ Synthetic demo data only. This system is not designed for real patient information.
    </p>
  </header>

  <form onsubmit={(e) => { e.preventDefault(); submit(); }} class="space-y-6">
    <!-- Demographics -->
    <section class="rounded-2xl border border-border bg-surface p-6">
      <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-5">
        Demographics
      </p>
      <div class="grid grid-cols-2 gap-4">
        <label class="block">
          <span class="text-sm text-text-muted mb-1.5 block">Age</span>
          <input type="number" bind:value={age} min="15" max="55" required
                 class="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm
                        focus:outline-none focus:border-text-muted" />
        </label>
        <label class="block">
          <span class="text-sm text-text-muted mb-1.5 block">Ethnicity</span>
          <select bind:value={ethnicity} required
                  class="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm
                         focus:outline-none focus:border-text-muted">
            <option value="black_african">Black African</option>
            <option value="east_asian">East Asian</option>
            <option value="south_asian">South Asian</option>
            <option value="white">White</option>
            <option value="other">Other</option>
            <option value="not_disclosed">Not Disclosed</option>
          </select>
        </label>
        <label class="block">
          <span class="text-sm text-text-muted mb-1.5 block">Socioeconomic Proxy</span>
          <select bind:value={socioeconomic_proxy} required
                  class="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm
                         focus:outline-none focus:border-text-muted">
            <option value="low">Low</option>
            <option value="middle">Middle</option>
            <option value="high">High</option>
          </select>
        </label>
        <label class="block">
          <span class="text-sm text-text-muted mb-1.5 block">Parity</span>
          <input type="number" bind:value={parity} min="0" max="10" required
                 class="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm
                        focus:outline-none focus:border-text-muted" />
        </label>
        <label class="block">
          <span class="text-sm text-text-muted mb-1.5 block">Current Gestational Week</span>
          <input type="number" bind:value={current_gestational_week} min="6" max="42" required
                 class="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm
                        focus:outline-none focus:border-text-muted" />
        </label>
        <label class="block">
          <span class="text-sm text-text-muted mb-1.5 block">BMI at Booking</span>
          <input type="number" bind:value={bmi_at_booking} step="0.1" min="15" max="60" required
                 class="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm
                        focus:outline-none focus:border-text-muted" />
        </label>
      </div>
    </section>

    <!-- Risk factors -->
    <section class="rounded-2xl border border-border bg-surface p-6">
      <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-5">
        Risk Factors
      </p>
      <div class="grid grid-cols-2 gap-3">
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" bind:checked={multiple_pregnancy} class="accent-approved" />
          Multiple pregnancy
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" bind:checked={pre_existing_hypertension} class="accent-approved" />
          Pre-existing hypertension
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" bind:checked={prior_preeclampsia} class="accent-approved" />
          Prior pre-eclampsia
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" bind:checked={family_history_preeclampsia} class="accent-approved" />
          Family history of pre-eclampsia
        </label>
        <label class="col-span-2 mt-2">
          <span class="text-sm text-text-muted mb-1.5 block">Diabetes</span>
          <select bind:value={diabetes}
                  class="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm
                         focus:outline-none focus:border-text-muted">
            <option value="none">None</option>
            <option value="gestational">Gestational</option>
            <option value="type1">Type 1</option>
            <option value="type2">Type 2</option>
          </select>
        </label>
      </div>
    </section>

    <!-- BP readings -->
    <section class="rounded-2xl border border-border bg-surface p-6">
      <div class="flex items-baseline justify-between mb-5">
        <p class="text-xs font-medium uppercase tracking-wider text-text-subtle">
          Blood Pressure Readings
        </p>
        <button type="button" onclick={addReading} class="text-xs text-approved hover:underline">
          + Add reading
        </button>
      </div>
      <p class="text-xs text-text-subtle mb-4">
        Trajectory across pregnancy is Sentinel's strongest predictive signal. Add 2–6 readings.
      </p>
      <div class="space-y-2">
        {#each bp_readings as reading, i}
          <div class="grid grid-cols-[1fr_1fr_1fr_auto] gap-2 items-center">
            <input type="number" bind:value={reading.gestational_week} min="6" max="42" placeholder="Week"
                   class="rounded-md border border-border bg-bg px-3 py-1.5 text-sm
                          focus:outline-none focus:border-text-muted" />
            <input type="number" bind:value={reading.systolic} min="70" max="200" placeholder="Systolic"
                   class="rounded-md border border-border bg-bg px-3 py-1.5 text-sm
                          focus:outline-none focus:border-text-muted" />
            <input type="number" bind:value={reading.diastolic} min="40" max="130" placeholder="Diastolic"
                   class="rounded-md border border-border bg-bg px-3 py-1.5 text-sm
                          focus:outline-none focus:border-text-muted" />
            <button type="button" onclick={() => removeReading(i)}
                    disabled={bp_readings.length <= 1}
                    class="text-text-subtle hover:text-error text-xs px-2 disabled:opacity-30">
              Remove
            </button>
          </div>
        {/each}
      </div>
    </section>

    <!-- Symptoms -->
    <section class="rounded-2xl border border-border bg-surface p-6">
      <p class="text-xs font-medium uppercase tracking-wider text-text-subtle mb-5">
        Current Symptoms
      </p>
      <div class="grid grid-cols-2 gap-3">
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" bind:checked={headache} class="accent-approved" /> Headache
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" bind:checked={visual_disturbance} class="accent-approved" /> Visual disturbance
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" bind:checked={epigastric_pain} class="accent-approved" /> Epigastric pain
        </label>
        <label class="flex items-center gap-2 text-sm">
          <input type="checkbox" bind:checked={swelling} class="accent-approved" /> Swelling
        </label>
        <label class="col-span-2 mt-2">
          <span class="text-sm text-text-muted mb-1.5 block">Proteinuria Level (optional, g/L)</span>
          <input type="number" bind:value={proteinuria_level} step="0.1" min="0" max="20"
                 placeholder="Leave blank if not measured"
                 class="w-full rounded-md border border-border bg-bg px-3 py-2 text-sm
                        focus:outline-none focus:border-text-muted" />
        </label>
      </div>
    </section>

    {#if error}
      <div class="rounded-xl border border-error bg-error/10 p-4">
        <p class="text-error font-medium text-sm mb-1">Validation failed</p>
        <p class="text-xs text-text-muted leading-relaxed">{error}</p>
      </div>
    {/if}

    <div class="flex justify-end gap-3">
      <a href="/" class="px-4 py-2 text-sm text-text-muted hover:text-text">Cancel</a>
      <button type="submit" disabled={submitting}
              class="px-4 py-2 text-sm font-medium rounded-md bg-approved/15 text-approved
                     border border-approved/30 hover:bg-approved/25 disabled:opacity-50">
        {submitting ? 'Running pipeline…' : 'Run Assessment'}
      </button>
    </div>
  </form>
</div>