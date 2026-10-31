// Pure helpers for turning run state / the report object into display and export data.

export const SECTION_ORDER = ["summary", "architecture", "diagram", "setup", "first_issues"];

const rank = (key) => {
  const i = SECTION_ORDER.indexOf(key);
  return i === -1 ? SECTION_ORDER.length : i;
};

/** Stable sort: known section keys in contract order, unknown keys after, in arrival order. */
export function orderSections(sections) {
  return sections
    .map((section, index) => ({ section, index }))
    .sort((a, b) => rank(a.section.key) - rank(b.section.key) || a.index - b.index)
    .map(({ section }) => section);
}

/** Strip a ```mermaid fence if the model wrapped its output in one (the contract says no fences). */
export function cleanMermaid(source) {
  if (typeof source !== "string") return "";
  const trimmed = source.trim();
  const fenced = trimmed.match(/^```(?:mermaid)?[ \t]*\r?\n([\s\S]*?)\r?\n?```$/i);
  return (fenced ? fenced[1] : trimmed).trim();
}

/** Sections of a finished report, filling in `summary`/`diagram` from the top-level fields if missing. */
export function sectionsFromReport(report) {
  const sections = Array.isArray(report?.sections) ? [...report.sections] : [];
  if (report?.summary && !sections.some((s) => s.key === "summary")) {
    sections.push({ key: "summary", title: "Overview", markdown: report.summary });
  }
  if (report?.mermaid && !sections.some((s) => s.key === "diagram")) {
    sections.push({ key: "diagram", title: "Architecture diagram", markdown: report.mermaid });
  }
  return orderSections(sections);
}

/**
 * What the report column should show. The finished report is authoritative; before it
 * arrives (or if fetching it failed) fall back to the sections streamed over SSE.
 */
export function getSections(state) {
  if (state.report && sectionsFromReport(state.report).length > 0) {
    return sectionsFromReport(state.report);
  }
  const streamed = Object.entries(state.sections).map(([key, value]) => ({
    key,
    title: value.title,
    markdown: value.markdown,
  }));
  return orderSections(streamed);
}

function issueLines(issues) {
  return issues.flatMap((issue, i) => [
    `${i + 1}. [#${issue.number} ${issue.title}](${issue.url}) (${issue.difficulty})`,
    `   - ${issue.reason}`,
  ]);
}

/** Render the whole report as Markdown for copy / download. */
export function reportToMarkdown(report) {
  const sections = sectionsFromReport(report);
  const issues = Array.isArray(report?.first_issues) ? report.first_issues : [];
  const lines = [`# Onboarding report: ${report?.repo ?? "repository"}`, ""];

  for (const section of sections) {
    lines.push(`## ${section.title}`, "");
    if (section.key === "diagram") {
      lines.push("```mermaid", cleanMermaid(section.markdown), "```", "");
    } else {
      if (section.markdown?.trim()) lines.push(section.markdown.trim(), "");
      if (section.key === "first_issues" && issues.length) lines.push(...issueLines(issues), "");
    }
  }

  if (issues.length && !sections.some((s) => s.key === "first_issues")) {
    lines.push("## Your first contributions", "", ...issueLines(issues), "");
  }
  return `${lines.join("\n").trimEnd()}\n`;
}

export function downloadFilename(repo) {
  const slug = String(repo ?? "report")
    .replace(/[^A-Za-z0-9_.-]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return `repopilot-${slug || "report"}.md`;
}
