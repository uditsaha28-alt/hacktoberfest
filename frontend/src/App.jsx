import DemoRepoChips from "./components/DemoRepoChips.jsx";
import ErrorBanner from "./components/ErrorBanner.jsx";
import RepoForm from "./components/RepoForm.jsx";
import { SparkIcon } from "./components/icons.jsx";
import { useRun } from "./hooks/useRun.js";
import RunPage from "./pages/RunPage.jsx";

function Brand() {
  return (
    <div className="flex items-center gap-2.5">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-white shadow-lg shadow-brand-600/30">
        <SparkIcon className="h-4 w-4" />
      </span>
      <span className="text-lg font-semibold tracking-tight text-white">RepoPilot</span>
    </div>
  );
}

function Landing({ state, onStart, onRetry, onDismiss }) {
  const busy = state.status === "starting";
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center px-4 py-16 text-center">
      <p className="mx-auto mb-4 inline-flex items-center gap-2 rounded-full border border-brand-400/30 bg-brand-500/10 px-3 py-1 text-xs font-medium text-brand-100">
        <SparkIcon className="h-3.5 w-3.5" /> Autonomous onboarding agent
      </p>
      <h1 className="text-4xl font-bold tracking-tight text-white sm:text-5xl">
        Understand any repo
        <span className="block bg-gradient-to-r from-brand-400 to-sky-300 bg-clip-text text-transparent">
          and ship your first PR.
        </span>
      </h1>
      <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-slate-400">
        Paste a public GitHub repository. RepoPilot plans its own exploration, reads the code, and hands you a
        summary, an architecture diagram, a setup guide and real issues matched to your skill level.
      </p>

      <div className="mt-10 space-y-4">
        <RepoForm onSubmit={onStart} busy={busy} initialValue={state.repoUrl} />
        <DemoRepoChips onSelect={onStart} disabled={busy} />
      </div>

      {state.status === "error" && (
        <div className="mt-8 text-left">
          <ErrorBanner message={state.error} onRetry={state.repoUrl ? onRetry : undefined} onDismiss={onDismiss} />
        </div>
      )}
    </div>
  );
}

export default function App() {
  const { state, start, retry, reset } = useRun();

  // Failures before a run exists (bad URL, 404, backend down) stay on the landing screen.
  const showRun = state.status !== "idle" && !(state.status === "error" && !state.runId);

  return (
    <div className="flex min-h-screen flex-col">
      <nav className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-5">
        <button type="button" onClick={reset} className="rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-400" aria-label="RepoPilot home">
          <Brand />
        </button>
        <span className="hidden text-xs text-slate-500 sm:block">Hacktoberfest Hack Day · CC Club MNNIT</span>
      </nav>

      {showRun ? (
        <RunPage state={state} onRetry={retry} onReset={reset} />
      ) : (
        <Landing state={state} onStart={start} onRetry={retry} onDismiss={reset} />
      )}

      <footer className="mx-auto w-full max-w-6xl px-4 py-6 text-center text-xs text-slate-600">
        Built with React, FastAPI and an LLM agent that decides what to read.
      </footer>
    </div>
  );
}
