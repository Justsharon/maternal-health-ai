<script lang="ts">
  type Variant = 'reliable' | 'reduced' | 'approved' | 'needs-review' | 'escalate' | 'in-scope' | 'out-of-scope';

  let { variant, label }: { variant: Variant; label: string } = $props();

  const styles: Record<Variant, string> = {
    'reliable':     'bg-reliable/15 text-reliable border-reliable/30',
    'reduced':      'bg-reduced/15 text-reduced border-reduced/30',
    'approved':     'bg-approved/15 text-approved border-approved/30',
    'needs-review': 'bg-needs-review/15 text-needs-review border-needs-review/30',
    'escalate':     'bg-escalate/15 text-escalate border-escalate/30',
    'in-scope':     'bg-approved/15 text-approved border-approved/30',
    'out-of-scope': 'bg-error/15 text-error border-error/30',
  };
</script>

<span class="inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium {styles[variant]}">
  <span class="size-1.5 rounded-full bg-current"></span>
  {label}
</span>