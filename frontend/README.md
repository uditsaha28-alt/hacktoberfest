# RepoPilot Frontend

React 18 + Vite + Tailwind UI for RepoPilot. It streams the agent's live plan, tool calls and observations over SSE and renders the final onboarding report.

## Run it

Requires Node 20+.

```bash
cd frontend
cp .env.example .env        # VITE_API_BASE_URL=http://localhost:8000
npm install
```

### Against the mock server (no backend needed)

```bash
npm run mock    # terminal 1: fake API + scripted SSE run on :8000
npm run dev     # terminal 2: UI on http://localhost:5173
```

Mock helpers: set `SPEED=0.3` for a faster run. Use these repo names to trigger states:

| Repo URL ends with | Result |
|---|---|
| `/notfound` | `404 repo_not_found` |
| `/ratelimit` | `429 rate_limited` |
| `/boom` | fatal `error` event mid-run |

### Against the real backend

Start the FastAPI backend on `:8000` (CORS must allow `http://localhost:5173`), then just `npm run dev`. Nothing else changes: the mock server implements the same contract (`docs/API_CONTRACT.md`).

## Test and build

```bash
npm test         # Vitest: validators, SSE helper, run reducer, report helpers, component smoke tests
npm run build    # production build in dist/
```

## Structure

```
src/
  api/        client.js (createRun, getReport, health), events.js (EventSource helper)
  hooks/      runReducer.js (pure state machine), useRun.js (hook)
  components/ RepoForm, DemoRepoChips, PlanPanel, ActivityFeed, ReportView, SectionCard,
              MermaidDiagram, IssueCard, StatusBadge, ErrorBanner, Markdown, icons
  pages/      RunPage.jsx
  lib/        validators.js, report.js (ordering + Markdown export), tools.js
  tests/
mock-server/  server.js + fixtures/ (events.json, report.json)
```

## Design notes

- **State** lives in one reducer (`runReducer.js`): `plan` replaces, `tool_call` pushes a pending item, `observation` resolves by `id`, `section` upserts by `key`, `done` triggers the report fetch.
- **SSE**: native `EventSource`, closed on `done`, `error` and unmount. A dropped connection surfaces as an error instead of auto-reconnecting, because a reconnect would replay the run from the start.
- **Plan progress** is indicative: the contract has no per-step status, so completed tool calls since the latest plan advance the active step.
- **Mermaid** is lazy-loaded, rendered with `securityLevel: "strict"`, wrapped in an error boundary, and falls back to raw source if the LLM's diagram is invalid.
- **Markdown** is rendered without raw HTML; links open in a new tab.
- **Demo repos** are the `DEMO_REPOS` constant in `DemoRepoChips.jsx`. Replace them with the final rehearsed picks.
