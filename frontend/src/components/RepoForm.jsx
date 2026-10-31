import { useState } from "react";
import { validateRepoUrl } from "../lib/validators.js";
import { ArrowRightIcon, GithubIcon, SpinnerIcon } from "./icons.jsx";

export default function RepoForm({ onSubmit, busy = false, initialValue = "" }) {
  const [value, setValue] = useState(initialValue);
  const [error, setError] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (busy) return;
    const result = validateRepoUrl(value);
    if (!result.valid) {
      setError(result.error);
      return;
    }
    setError("");
    onSubmit(result.url);
  };

  return (
    <form onSubmit={handleSubmit} noValidate className="w-full">
      <label htmlFor="repo-url" className="sr-only">
        GitHub repository URL
      </label>
      <div
        className={`flex flex-col gap-2 rounded-2xl border bg-ink-800/80 p-2 shadow-xl shadow-black/20 sm:flex-row sm:items-center ${
          error ? "border-rose-400/50" : "border-white/10 focus-within:border-brand-400/60"
        }`}
      >
        <div className="flex flex-1 items-center gap-3 px-3">
          <GithubIcon className="h-5 w-5 shrink-0 text-slate-400" />
          <input
            id="repo-url"
            type="url"
            inputMode="url"
            autoComplete="off"
            spellCheck={false}
            placeholder="https://github.com/owner/name"
            value={value}
            disabled={busy}
            aria-invalid={error ? "true" : "false"}
            aria-describedby={error ? "repo-url-error" : undefined}
            onChange={(e) => {
              setValue(e.target.value);
              if (error) setError("");
            }}
            className="w-full bg-transparent py-3 font-mono text-sm text-white placeholder:text-slate-500 focus:outline-none disabled:opacity-60"
          />
        </div>
        <button type="submit" className="btn-primary py-3" disabled={busy}>
          {busy ? (
            <>
              <SpinnerIcon /> Starting…
            </>
          ) : (
            <>
              Analyze repo <ArrowRightIcon />
            </>
          )}
        </button>
      </div>
      {error && (
        <p id="repo-url-error" role="alert" className="mt-2 px-2 text-sm text-rose-300">
          {error}
        </p>
      )}
    </form>
  );
}
