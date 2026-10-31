import { useEffect, useRef } from "react";
import { argsPreview, toolIconName, toolLabel } from "../lib/tools.js";
import {
  CheckIcon,
  FileIcon,
  IssueIcon,
  PenIcon,
  SearchIcon,
  SpinnerIcon,
  TreeIcon,
  XIcon,
} from "./icons.jsx";

const TOOL_ICONS = {
  tree: TreeIcon,
  file: FileIcon,
  search: SearchIcon,
  issue: IssueIcon,
  pen: PenIcon,
};

function StatusIcon({ status }) {
  if (status === "ok") {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-400/15 text-emerald-300" title="Succeeded">
        <CheckIcon className="h-3.5 w-3.5" />
      </span>
    );
  }
  if (status === "failed") {
    return (
      <span className="flex h-6 w-6 items-center justify-center rounded-full bg-rose-400/15 text-rose-300" title="Failed">
        <XIcon className="h-3.5 w-3.5" />
      </span>
    );
  }
  return (
    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-brand-500/15 text-brand-100" title="Running">
      <SpinnerIcon className="h-3.5 w-3.5" />
    </span>
  );
}

export default function ActivityFeed({ activity, status }) {
  const scrollRef = useRef(null);

  // Keep the newest entry in view as the agent works.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [activity]);

  const waiting = activity.length === 0 && (status === "starting" || status === "running");

  return (
    <section className="card flex min-h-0 flex-col p-5" aria-labelledby="activity-heading">
      <div className="mb-4 flex items-center justify-between">
        <h2 id="activity-heading" className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Live activity
        </h2>
        <span className="font-mono text-xs text-slate-500">
          {activity.length} tool call{activity.length === 1 ? "" : "s"}
        </span>
      </div>

      {activity.length === 0 ? (
        <p className="flex items-center gap-2 text-sm text-slate-400">
          {waiting && <SpinnerIcon />} {waiting ? "The agent hasn't picked a tool yet…" : "No activity yet."}
        </p>
      ) : (
        <ol
          ref={scrollRef}
          aria-live="polite"
          className="-mr-2 max-h-[26rem] space-y-3 overflow-y-auto pr-2"
        >
          {activity.map((item) => {
            const Icon = TOOL_ICONS[toolIconName(item.tool)] ?? FileIcon;
            const target = argsPreview(item.args);
            return (
              <li
                key={item.id}
                data-status={item.status}
                className={`animate-fadeUp rounded-xl border p-3 ${
                  item.status === "failed"
                    ? "border-rose-400/25 bg-rose-500/5"
                    : "border-white/10 bg-white/[0.03]"
                }`}
              >
                <div className="flex items-center gap-3">
                  <Icon className="h-4 w-4 shrink-0 text-slate-400" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-white">{toolLabel(item.tool)}</p>
                    {target && (
                      <p className="truncate font-mono text-xs text-brand-100/80" title={target}>
                        {target}
                      </p>
                    )}
                  </div>
                  <StatusIcon status={item.status} />
                </div>
                {item.summary && (
                  <p
                    className={`mt-2 border-t border-white/5 pt-2 text-xs leading-relaxed ${
                      item.status === "failed" ? "text-rose-200/90" : "text-slate-400"
                    }`}
                  >
                    {item.summary}
                  </p>
                )}
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
