const STYLES = {
  idle: { label: "Idle", dot: "bg-slate-400", chip: "border-white/10 bg-white/5 text-slate-300" },
  starting: {
    label: "Starting",
    dot: "bg-amber-400 animate-pulseDot",
    chip: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  },
  running: {
    label: "Agent working",
    dot: "bg-brand-400 animate-pulseDot",
    chip: "border-brand-400/30 bg-brand-500/10 text-brand-100",
  },
  done: { label: "Complete", dot: "bg-emerald-400", chip: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200" },
  error: { label: "Failed", dot: "bg-rose-400", chip: "border-rose-400/30 bg-rose-400/10 text-rose-200" },
};

export default function StatusBadge({ status }) {
  const style = STYLES[status] ?? STYLES.idle;
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-medium ${style.chip}`}
      role="status"
    >
      <span className={`h-2 w-2 rounded-full ${style.dot}`} />
      {style.label}
    </span>
  );
}
