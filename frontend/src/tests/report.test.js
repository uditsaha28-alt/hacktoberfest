import {
  cleanMermaid,
  downloadFilename,
  getSections,
  orderSections,
  reportToMarkdown,
  sectionsFromReport,
} from "../lib/report.js";

const report = {
  repo: "demo/demo-api",
  summary: "A small API.",
  sections: [
    { key: "setup", title: "Run it locally", markdown: "npm install" },
    { key: "summary", title: "Overview", markdown: "A small API." },
    { key: "diagram", title: "Architecture diagram", markdown: "graph TD\n  A-->B" },
    { key: "first_issues", title: "Your first contributions", markdown: "Ranked easiest first." },
  ],
  mermaid: "graph TD\n  A-->B",
  first_issues: [
    { number: 42, title: "Fix typo", url: "https://github.com/demo/demo-api/issues/42", reason: "Docs only", difficulty: "easy" },
  ],
};

describe("cleanMermaid", () => {
  it("returns plain source untouched (trimmed)", () => {
    expect(cleanMermaid("  graph TD\n  A-->B  ")).toBe("graph TD\n  A-->B");
  });

  it("strips a mermaid code fence", () => {
    expect(cleanMermaid("```mermaid\ngraph TD\n  A-->B\n```")).toBe("graph TD\n  A-->B");
  });

  it("strips a bare code fence", () => {
    expect(cleanMermaid("```\ngraph TD\n```")).toBe("graph TD");
  });

  it("handles non-strings", () => {
    expect(cleanMermaid(undefined)).toBe("");
    expect(cleanMermaid(null)).toBe("");
  });
});

describe("orderSections", () => {
  it("orders known keys by the contract and keeps unknown keys last in arrival order", () => {
    const ordered = orderSections([
      { key: "extra_b" },
      { key: "first_issues" },
      { key: "summary" },
      { key: "extra_a" },
      { key: "diagram" },
    ]);
    expect(ordered.map((s) => s.key)).toEqual(["summary", "diagram", "first_issues", "extra_b", "extra_a"]);
  });
});

describe("sectionsFromReport / getSections", () => {
  it("orders report sections", () => {
    expect(sectionsFromReport(report).map((s) => s.key)).toEqual(["summary", "diagram", "setup", "first_issues"]);
  });

  it("fills in a missing summary and diagram from top-level fields", () => {
    const sparse = { repo: "a/b", summary: "Hi", mermaid: "graph TD\n A-->B", sections: [] };
    expect(sectionsFromReport(sparse).map((s) => s.key)).toEqual(["summary", "diagram"]);
  });

  it("prefers the finished report over streamed sections", () => {
    const state = { report, sections: { summary: { title: "Old", markdown: "old" } } };
    expect(getSections(state)[0].title).toBe("Overview");
  });

  it("falls back to streamed sections before the report arrives", () => {
    const state = {
      report: null,
      sections: {
        setup: { title: "Setup", markdown: "s" },
        summary: { title: "Overview", markdown: "o" },
      },
    };
    expect(getSections(state).map((s) => s.key)).toEqual(["summary", "setup"]);
  });
});

describe("reportToMarkdown", () => {
  const md = reportToMarkdown(report);

  it("starts with the repo title", () => {
    expect(md.startsWith("# Onboarding report: demo/demo-api")).toBe(true);
  });

  it("fences the diagram as mermaid", () => {
    expect(md).toContain("```mermaid\ngraph TD\n  A-->B\n```");
  });

  it("lists first issues with links, difficulty and reason", () => {
    expect(md).toContain("1. [#42 Fix typo](https://github.com/demo/demo-api/issues/42) (easy)");
    expect(md).toContain("   - Docs only");
  });

  it("appends issues even when there is no first_issues section", () => {
    const noSection = { ...report, sections: report.sections.filter((s) => s.key !== "first_issues") };
    expect(reportToMarkdown(noSection)).toContain("## Your first contributions");
  });

  it("ends with a single trailing newline", () => {
    expect(md.endsWith("\n")).toBe(true);
    expect(md.endsWith("\n\n")).toBe(false);
  });
});

describe("downloadFilename", () => {
  it("makes a safe file name from the repo", () => {
    expect(downloadFilename("demo/demo-api")).toBe("repopilot-demo-demo-api.md");
    expect(downloadFilename("we ird/na*me")).toBe("repopilot-we-ird-na-me.md");
    expect(downloadFilename("")).toBe("repopilot-report.md");
  });
});
