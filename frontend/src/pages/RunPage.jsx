import ActivityFeed from "../components/ActivityFeed.jsx";
import ErrorBanner from "../components/ErrorBanner.jsx";
import PlanPanel from "../components/PlanPanel.jsx";
import ReportView from "../components/ReportView.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { ExternalIcon } from "../components/icons.jsx";
import { parseGithubUrl } from "../lib/validators.js";

export default function RunPage({ state, onRetry, onReset }) {
  const repo = parseGithubUrl(state.repoUrl);

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs uppercase tracking-wider text-slate-500">Onboarding report for</p>
          {repo ? (
            <a
              href={repo.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 truncate font-mono text-xl font-semibold text-white hover:text-brand-100"
            >
              {repo.owner}/{repo.name} <ExternalIcon className="h-4 w-4 text-slate-500" />
            </a>
          ) : (
            <p className="truncate font-mono text-xl font-semibold text-white">{state.repoUrl}</p>
          )}
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={state.status} />
          <button type="button" className="btn-ghost" onClick={onReset}>
            New analysis
          </button>
        </div>
      </header>

      {state.status === "error" && (
        <div className="mb-6">
          <ErrorBanner message={state.error} onRetry={onRetry} />
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="min-w-0 space-y-6 lg:col-span-2">
          <PlanPanel
            plan={state.plan}
            planRevision={state.planRevision}
            planStartedAt={state.planStartedAt}
            activity={state.activity}
            status={state.status}
          />
          <ActivityFeed activity={state.activity} status={state.status} />
        </div>

        <div className="min-w-0 lg:col-span-3">
          <ReportView state={state} />
        </div>
      </div>
    </div>
  );
}
