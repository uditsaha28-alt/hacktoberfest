import { fireEvent, render, screen } from "@testing-library/react";
import ActivityFeed from "../components/ActivityFeed.jsx";
import ErrorBanner from "../components/ErrorBanner.jsx";
import PlanPanel from "../components/PlanPanel.jsx";
import RepoForm from "../components/RepoForm.jsx";
import StatusBadge from "../components/StatusBadge.jsx";

describe("RepoForm", () => {
  it("shows a validation error and does not submit invalid input", () => {
    const onSubmit = vi.fn();
    render(<RepoForm onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText(/github repository url/i), { target: { value: "nope" } });
    fireEvent.click(screen.getByRole("button", { name: /analyze repo/i }));
    expect(screen.getByRole("alert").textContent).toContain("owner/name");
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("submits the normalized url when valid", () => {
    const onSubmit = vi.fn();
    render(<RepoForm onSubmit={onSubmit} />);
    fireEvent.change(screen.getByLabelText(/github repository url/i), {
      target: { value: " https://github.com/a/b/ " },
    });
    fireEvent.click(screen.getByRole("button", { name: /analyze repo/i }));
    expect(onSubmit).toHaveBeenCalledWith("https://github.com/a/b");
  });

  it("disables the button while busy", () => {
    render(<RepoForm onSubmit={() => {}} busy />);
    expect(screen.getByRole("button", { name: /starting/i }).disabled).toBe(true);
  });
});

describe("PlanPanel", () => {
  const base = { plan: ["Read tree", "Write report"], planStartedAt: 0, activity: [], status: "running" };

  it("shows the plan steps", () => {
    render(<PlanPanel {...base} planRevision={1} />);
    expect(screen.getByText("Read tree")).toBeTruthy();
    expect(screen.queryByText(/replanned/i)).toBeNull();
  });

  it("shows a replanned badge after the plan changes", () => {
    render(<PlanPanel {...base} planRevision={2} />);
    expect(screen.getByText(/replanned ×1/i)).toBeTruthy();
  });
});

describe("ActivityFeed", () => {
  it("renders tool calls with their status and summary", () => {
    const activity = [
      { id: "t1", tool: "read_file", args: { path: "README.md" }, status: "ok", summary: "Read README.md (2.1 KB)" },
      { id: "t2", tool: "read_file", args: { path: "nope.js" }, status: "failed", summary: "File not found" },
      { id: "t3", tool: "search_code", args: { query: "listen" }, status: "pending", summary: "" },
    ];
    const { container } = render(<ActivityFeed activity={activity} status="running" />);
    expect(screen.getByText("README.md")).toBeTruthy();
    expect(screen.getByText("File not found")).toBeTruthy();
    expect(container.querySelector('[data-status="failed"]')).not.toBeNull();
    expect(container.querySelector('[data-status="pending"]')).not.toBeNull();
  });

  it("shows a waiting message before the first tool call", () => {
    render(<ActivityFeed activity={[]} status="running" />);
    expect(screen.getByText(/hasn't picked a tool yet/i)).toBeTruthy();
  });
});

describe("ErrorBanner and StatusBadge", () => {
  it("renders the message and wires the retry button", () => {
    const onRetry = vi.fn();
    render(<ErrorBanner message="Backend down" onRetry={onRetry} />);
    expect(screen.getByRole("alert").textContent).toContain("Backend down");
    fireEvent.click(screen.getByRole("button", { name: /retry/i }));
    expect(onRetry).toHaveBeenCalled();
  });

  it("renders nothing without a message", () => {
    const { container } = render(<ErrorBanner message={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("labels each status", () => {
    render(<StatusBadge status="done" />);
    expect(screen.getByText("Complete")).toBeTruthy();
  });
});
