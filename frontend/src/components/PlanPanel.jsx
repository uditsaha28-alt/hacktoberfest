import { CheckIcon, SpinnerIcon } from "./icons.jsx";

/**
 * The contract has no per-step progress, so progress is indicative: completed tool calls
 * since this plan arrived advance the active step. The last step ("Write report") stays
 * active until the run is done.
 */
export function planProgress({ plan, activity, planStartedAt, status }) {
  if (status === "done") return plan.length;
  const resolvedSincePlan = activity.slice(planStartedAt).filter((a) => a.status !== "pending").length;
  return Math.min(resolvedSincePlan, Math.max(plan.length - 1, 0));
}

export default function PlanPanel({ plan, planRevision, planStartedAt, activity, status }) {
  const running = status === "running" || status === "starting";
  const doneCount = planProgress({ plan, activity, planStartedAt, status });

  return (
    <section className="card p-5" aria-labelledby="plan-heading">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 id="plan-heading" className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Agent plan
        </h2>
        {planRevision > 1 && (
          <span
            key={planRevision}
            className="animate-fadeUp rounded-full border border-amber-400/30 bg-amber-400/10 px-2.5 py-0.5 text-xs font-medium text-amber-200"
          >
            Replanned ×{planRevision - 1}
          </span>
        )}
      </div>

      {plan.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-slate-400">
          {running && <SpinnerIcon />} Waiting for the agent to make a plan…
        </p>
      ) : (
        <ol key={planRevision} className="space-y-2.5">
          {plan.map((step, i) => {
            const state = i < doneCount ? "done" : i === doneCount && running ? "active" : "pending";
            return (
              <li
                key={`${i}-${step}`}
                data-state={state}
                className="flex animate-fadeUp items-start gap-3 text-sm"
                style={{ animationDelay: `${i * 40}ms` }}
              >
                <span
                  className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${
                    state === "done"
                      ? "border-emerald-400/50 bg-emerald-400/15 text-emerald-300"
                      : state === "active"
                        ? "border-brand-400/60 bg-brand-500/15 text-brand-100"
                        : "border-white/15 text-transparent"
                  }`}
                >
                  {state === "done" && <CheckIcon className="h-3 w-3" />}
                  {state === "active" && <SpinnerIcon className="h-3 w-3" />}
                </span>
                <span
                  className={
                    state === "done"
                      ? "text-slate-400 line-through decoration-slate-600"
                      : state === "active"
                        ? "font-medium text-white"
                        : "text-slate-400"
                  }
                >
                  {step}
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
