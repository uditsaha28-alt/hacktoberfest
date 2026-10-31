import { AlertIcon, RefreshIcon } from "./icons.jsx";

export default function ErrorBanner({ message, onRetry, onDismiss }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      className="flex flex-col gap-3 rounded-2xl border border-rose-400/30 bg-rose-500/10 p-4 text-rose-100 sm:flex-row sm:items-center"
    >
      <div className="flex flex-1 items-start gap-3">
        <AlertIcon className="mt-0.5 h-5 w-5 shrink-0 text-rose-300" />
        <p className="text-sm leading-relaxed">{message}</p>
      </div>
      <div className="flex gap-2">
        {onRetry && (
          <button type="button" className="btn-ghost" onClick={onRetry}>
            <RefreshIcon /> Retry
          </button>
        )}
        {onDismiss && (
          <button type="button" className="btn-ghost" onClick={onDismiss}>
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
}
