import { ExternalIcon } from "./icons.jsx";

const DIFFICULTY = {
  easy: "border-emerald-400/30 bg-emerald-400/10 text-emerald-200",
  medium: "border-amber-400/30 bg-amber-400/10 text-amber-200",
  hard: "border-rose-400/30 bg-rose-400/10 text-rose-200",
};

export default function IssueCard({ issue, rank }) {
  const difficulty = String(issue.difficulty ?? "").toLowerCase();
  const safeUrl = typeof issue.url === "string" && issue.url.startsWith("https://") ? issue.url : null;

  return (
    <li className="rounded-xl border border-white/10 bg-white/[0.03] p-4 transition hover:border-brand-400/40">
      <div className="flex items-start gap-3">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-brand-500/15 font-mono text-xs font-semibold text-brand-100">
          {rank}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h4 className="font-medium text-white">
              <span className="mr-1.5 font-mono text-sm text-slate-500">#{issue.number}</span>
              {issue.title}
            </h4>
            {difficulty && (
              <span
                className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${
                  DIFFICULTY[difficulty] ?? "border-white/10 bg-white/5 text-slate-300"
                }`}
              >
                {difficulty}
              </span>
            )}
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{issue.reason}</p>
          {safeUrl && (
            <a
              href={safeUrl}
              target="_blank"
              rel="noreferrer noopener"
              className="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-brand-400 hover:text-brand-100"
            >
              Open on GitHub <ExternalIcon className="h-3.5 w-3.5" />
            </a>
          )}
        </div>
      </div>
    </li>
  );
}
