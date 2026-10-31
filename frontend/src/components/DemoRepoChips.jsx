// Rehearsed demo repos. Swap these for the final picks (small/medium, well structured,
// with open beginner issues) once the team has tested them end to end.
export const DEMO_REPOS = [
  { label: "tj/commander.js", url: "https://github.com/tj/commander.js" },
  { label: "pallets/click", url: "https://github.com/pallets/click" },
  { label: "sindresorhus/got", url: "https://github.com/sindresorhus/got" },
];

export default function DemoRepoChips({ onSelect, disabled = false }) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-2">
      <span className="text-xs uppercase tracking-wider text-slate-500">Try one</span>
      {DEMO_REPOS.map((repo) => (
        <button
          key={repo.url}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(repo.url)}
          className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 font-mono text-xs text-slate-300 transition hover:border-brand-400/50 hover:bg-brand-500/10 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400 disabled:opacity-50"
        >
          {repo.label}
        </button>
      ))}
    </div>
  );
}
