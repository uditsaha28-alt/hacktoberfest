/**
 * Pure state machine for a run (see docs/ROADMAP.md, 9.2).
 *
 * status: idle | starting | running | done | error
 */

export const initialState = {
  status: "idle",
  runId: null,
  repoUrl: "",
  plan: [],
  planRevision: 0, // increments each time the agent (re)plans; > 1 means it replanned
  planStartedAt: 0, // activity.length when the current plan arrived (drives plan progress)
  activity: [], // [{ id, tool, args, status: "pending" | "ok" | "failed", summary }]
  sections: {}, // { [key]: { title, markdown } }, keyed so a repeat replaces
  report: null,
  error: null,
};

const TERMINAL = new Set(["done", "error"]);

function applyEvent(state, name, data) {
  switch (name) {
    case "plan": {
      if (!Array.isArray(data?.steps)) return state;
      return {
        ...state,
        plan: data.steps.map(String),
        planRevision: state.planRevision + 1,
        planStartedAt: state.activity.length,
      };
    }

    case "tool_call": {
      if (state.activity.some((a) => a.id === data.id)) return state;
      return {
        ...state,
        activity: [
          ...state.activity,
          { id: data.id, tool: data.tool, args: data.args ?? {}, status: "pending", summary: "" },
        ],
      };
    }

    case "observation": {
      const status = data.ok ? "ok" : "failed";
      const summary = data.summary ?? "";
      const exists = state.activity.some((a) => a.id === data.id);
      const activity = exists
        ? state.activity.map((a) => (a.id === data.id ? { ...a, status, summary } : a))
        : [...state.activity, { id: data.id, tool: "unknown", args: {}, status, summary }];
      return { ...state, activity };
    }

    case "section": {
      if (!data?.key) return state;
      return {
        ...state,
        sections: {
          ...state.sections,
          [data.key]: { title: data.title ?? data.key, markdown: data.markdown ?? "" },
        },
      };
    }

    case "done":
      return { ...state, status: "done" };

    case "error":
      return { ...state, status: "error", error: data?.message || "Something went wrong." };

    default:
      return state;
  }
}

export function runReducer(state, action) {
  switch (action.type) {
    case "START":
      return { ...initialState, status: "starting", repoUrl: action.repoUrl };

    case "RUN_CREATED":
      return { ...state, status: "running", runId: action.runId };

    case "EVENT":
      // The stream ends after done/error, so ignore anything that arrives late.
      if (TERMINAL.has(state.status)) return state;
      return applyEvent(state, action.name, action.data ?? {});

    case "REPORT_LOADED":
      return { ...state, report: action.report };

    case "FAIL":
      return { ...state, status: "error", error: action.message };

    case "RESET":
      return initialState;

    default:
      return state;
  }
}
