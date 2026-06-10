<script lang="ts">
  let { reason }: { reason: string } = $props();
</script>

<section class="rounded-3xl border border-reduced/40 bg-reduced/10 p-8">
  <div class="flex gap-4">
    <svg class="size-6 text-reduced shrink-0 mt-0.5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path fill-rule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.17 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"/>
    </svg>
    <div class="flex-1">
      <p class="text-sm font-semibold text-reduced mb-2">Reduced reliability for this prediction</p>
      <p class="text-[14px] text-text leading-relaxed">{reason}</p>
    </div>
  </div>
</section>