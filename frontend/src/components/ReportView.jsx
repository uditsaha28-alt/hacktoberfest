import { useEffect, useState } from "react";
import { downloadFilename, getSections, reportToMarkdown } from "../lib/report.js";
import { parseGithubUrl } from "../lib/validators.js";
import IssueCard from "./IssueCard.jsx";
import Markdown from "./Markdown.jsx";
import MermaidDiagram from "./MermaidDiagram.jsx";
import SectionCard from "./SectionCard.jsx";
import { CheckIcon, CopyIcon, DownloadIcon, SpinnerIcon } from "./icons.jsx";

function Skeleton() {
  return (
    <div className="card animate-pulse space-y-3 p-6" aria-hidden="true">
      <div className="h-4 w-1/3 rounded bg-white/10" />
      <div className="h-3 w-full rounded bg-white/5" />
      <div className="h-3 w-5/6 rounded bg-white/5" />
      <div className="h-3 w-2/3 rounded bg-white/5" />
    </div>
  );
}

export default function ReportView({ state }) {
  const { status, report } = state;
  const [copied, setCopied] = useState(false);
  const [copyFailed, setCopyFailed] = useState(false);

  const sections = getSections(state);
  const issues = Array.isArray(report?.first_issues) ? report.first_issues : [];
  const parsed = parseGithubUrl(state.repoUrl);
  const repoName = report?.repo ?? (parsed ? `${parsed.owner}/${parsed.name}` : state.repoUrl);
  const canExport = status === "done" && sections.length > 0;
  const hasIssuesSection = sections.some((s) => s.key === "first_issues");

  useEffect(() => {
    if (!copied && !copyFailed) return undefined;
    const timer = setTimeout(() => {
      setCopied(false);
      setCopyFailed(false);
    }, 2000);
    return () => clearTimeout(timer);
  }, [copied, copyFailed]);

  const exportMarkdown = () =>
    reportToMarkdown(report ?? { repo: repoName, sections, mermaid: "", first_issues: [] });

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(exportMarkdown());
      setCopied(true);
    } catch {
      setCopyFailed(true);
    }
  };

  const handleDownload = () => {
    const blob = new Blob([exportMarkdown()], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = downloadFilename(repoName);
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4" aria-live="polite">
      {canExport && (
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm text-slate-400">Your onboarding report is ready.</p>
          <div className="flex gap-2">
            <button type="button" className="btn-ghost" onClick={handleCopy}>
              {copied ? <CheckIcon className="h-4 w-4 text-emerald-300" /> : <CopyIcon />}
              {copied ? "Copied!" : copyFailed ? "Copy failed" : "Copy as Markdown"}
            </button>
            <button type="button" className="btn-ghost" onClick={handleDownload}>
              <DownloadIcon /> Download report
            </button>
          </div>
        </div>
      )}

      {sections.length === 0 ? (
        status === "running" || status === "starting" ? (
          <>
            <p className="flex items-center gap-2 text-sm text-slate-400">
              <SpinnerIcon /> The report builds up here as the agent writes each section.
            </p>
            <Skeleton />
            <Skeleton />
          </>
        ) : status === "done" ? (
          <div className="card p-6 text-sm text-slate-400">The run finished without producing any sections.</div>
        ) : (
          <div className="card p-6 text-sm text-slate-400">No report content yet.</div>
        )
      ) : (
        sections.map((section) => (
          <SectionCard key={section.key} title={section.title}>
            {section.key === "diagram" ? (
              <MermaidDiagram source={section.markdown} />
            ) : (
              <>
                {section.markdown && <Markdown>{section.markdown}</Markdown>}
                {section.key === "first_issues" && issues.length > 0 && (
                  <ol className="mt-4 space-y-3">
                    {issues.map((issue, i) => (
                      <IssueCard key={issue.number ?? i} issue={issue} rank={i + 1} />
                    ))}
                  </ol>
                )}
              </>
            )}
          </SectionCard>
        ))
      )}

      {!hasIssuesSection && issues.length > 0 && (
        <SectionCard title="Your first contributions">
          <ol className="space-y-3">
            {issues.map((issue, i) => (
              <IssueCard key={issue.number ?? i} issue={issue} rank={i + 1} />
            ))}
          </ol>
        </SectionCard>
      )}

      {status === "done" && !report && sections.length > 0 && (
        <p className="flex items-center gap-2 text-xs text-slate-500">
          <SpinnerIcon className="h-3 w-3" /> Finalizing report…
        </p>
      )}
    </div>
  );
}
