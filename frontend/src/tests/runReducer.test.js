import { initialState, runReducer } from "../hooks/runReducer.js";

const ev = (name, data) => ({ type: "EVENT", name, data });
const running = () =>
  runReducer(runReducer(initialState, { type: "START", repoUrl: "https://github.com/a/b" }), {
    type: "RUN_CREATED",
    runId: "r1",
  });

describe("runReducer lifecycle", () => {
  it("START resets state and enters starting", () => {
    const dirty = { ...initialState, status: "error", error: "x", plan: ["old"] };
    const next = runReducer(dirty, { type: "START", repoUrl: "https://github.com/a/b" });
    expect(next.status).toBe("starting");
    expect(next.repoUrl).toBe("https://github.com/a/b");
    expect(next.error).toBeNull();
    expect(next.plan).toEqual([]);
  });

  it("RUN_CREATED moves to running and stores the id", () => {
    const s = running();
    expect(s.status).toBe("running");
    expect(s.runId).toBe("r1");
  });

  it("FAIL sets error status and message", () => {
    const s = runReducer(running(), { type: "FAIL", message: "boom" });
    expect(s.status).toBe("error");
    expect(s.error).toBe("boom");
  });

  it("RESET returns to the initial state", () => {
    expect(runReducer(running(), { type: "RESET" })).toEqual(initialState);
  });

  it("REPORT_LOADED stores the report", () => {
    const report = { repo: "a/b" };
    expect(runReducer(running(), { type: "REPORT_LOADED", report }).report).toEqual(report);
  });
});

describe("runReducer events", () => {
  it("plan replaces the previous plan (replan)", () => {
    let s = runReducer(running(), ev("plan", { steps: ["a", "b", "c"] }));
    expect(s.plan).toEqual(["a", "b", "c"]);
    s = runReducer(s, ev("plan", { steps: ["x", "y"] }));
    expect(s.plan).toEqual(["x", "y"]);
  });

  it("plan counts revisions so the UI can show a replan", () => {
    let s = runReducer(running(), ev("plan", { steps: ["a"] }));
    expect(s.planRevision).toBe(1);
    s = runReducer(s, ev("plan", { steps: ["b"] }));
    expect(s.planRevision).toBe(2);
  });

  it("plan records how much activity existed when it arrived", () => {
    let s = runReducer(running(), ev("tool_call", { id: "t1", tool: "read_file", args: {} }));
    s = runReducer(s, ev("plan", { steps: ["a"] }));
    expect(s.planStartedAt).toBe(1);
  });

  it("ignores a malformed plan payload", () => {
    const s = runReducer(running(), ev("plan", { steps: "nope" }));
    expect(s.plan).toEqual([]);
  });

  it("tool_call pushes a pending activity", () => {
    const s = runReducer(running(), ev("tool_call", { id: "t1", tool: "read_file", args: { path: "README.md" } }));
    expect(s.activity).toHaveLength(1);
    expect(s.activity[0].status).toBe("pending");
    expect(s.activity[0].args).toEqual({ path: "README.md" });
  });

  it("does not duplicate a tool_call with a repeated id", () => {
    let s = runReducer(running(), ev("tool_call", { id: "t1", tool: "read_file", args: {} }));
    s = runReducer(s, ev("tool_call", { id: "t1", tool: "read_file", args: {} }));
    expect(s.activity).toHaveLength(1);
  });

  it("observation resolves the matching activity as ok", () => {
    let s = runReducer(running(), ev("tool_call", { id: "t1", tool: "read_file", args: {} }));
    s = runReducer(s, ev("tool_call", { id: "t2", tool: "search_code", args: {} }));
    s = runReducer(s, ev("observation", { id: "t1", ok: true, summary: "Read it" }));
    expect(s.activity[0].status).toBe("ok");
    expect(s.activity[0].summary).toBe("Read it");
    expect(s.activity[1].status).toBe("pending");
  });

  it("observation with ok:false marks the activity failed", () => {
    let s = runReducer(running(), ev("tool_call", { id: "t1", tool: "read_file", args: {} }));
    s = runReducer(s, ev("observation", { id: "t1", ok: false, summary: "Not found" }));
    expect(s.activity[0].status).toBe("failed");
  });

  it("observation with an unknown id is kept rather than dropped", () => {
    const s = runReducer(running(), ev("observation", { id: "zz", ok: true, summary: "late" }));
    expect(s.activity).toHaveLength(1);
    expect(s.activity[0].tool).toBe("unknown");
  });

  it("section upserts by key and replaces on repeat", () => {
    let s = runReducer(running(), ev("section", { key: "summary", title: "Overview", markdown: "v1" }));
    s = runReducer(s, ev("section", { key: "setup", title: "Setup", markdown: "s" }));
    s = runReducer(s, ev("section", { key: "summary", title: "Overview", markdown: "v2" }));
    expect(Object.keys(s.sections)).toEqual(["summary", "setup"]);
    expect(s.sections.summary.markdown).toBe("v2");
  });

  it("done sets status done", () => {
    expect(runReducer(running(), ev("done", {})).status).toBe("done");
  });

  it("error event sets status error with the message", () => {
    const s = runReducer(running(), ev("error", { message: "rate limited" }));
    expect(s.status).toBe("error");
    expect(s.error).toBe("rate limited");
  });

  it("ignores events that arrive after the run finished", () => {
    let s = runReducer(running(), ev("done", {}));
    s = runReducer(s, ev("plan", { steps: ["late"] }));
    expect(s.plan).toEqual([]);
  });

  it("still accepts REPORT_LOADED after done", () => {
    let s = runReducer(running(), ev("done", {}));
    s = runReducer(s, { type: "REPORT_LOADED", report: { repo: "a/b" } });
    expect(s.status).toBe("done");
    expect(s.report).toEqual({ repo: "a/b" });
  });
});
