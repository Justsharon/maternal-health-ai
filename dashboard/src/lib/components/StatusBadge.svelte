<script lang="ts">
  type Variant = 'reliable' | 'reduced' | 'approved' | 'needs-review' | 'escalate' | 'in-scope' | 'out-of-scope';

  let { variant, label }: { variant: Variant; label: string } = $props();

  const styles: Record<Variant, string> = {
    'reliable':     'bg-emerald-400/15 text-emerald-400 border-emerald-400/30',
    'reduced':      'bg-amber-400/15 text-amber-400 border-amber-400/30',
    'approved':     'bg-sky-400/15 text-sky-400 border-sky-400/30',
    'needs-review': 'bg-yellow-400/15 text-yellow-400 border-yellow-400/30',
    'escalate':     'bg-violet-500/15 text-violet-500 border-violet-500/30',
    'in-scope':     'bg-sky-400/15 text-sky-400 border-sky-400/30',
    'out-of-scope': 'bg-[#DC143C]/15 text-[#DC143C] border-[#DC143C]/30',
  };
</script>

<span class="inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium {styles[variant]}">
  <span class="size-1.5 rounded-full bg-current"></span>
  {label}
</span>