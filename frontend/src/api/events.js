import { eventsUrl } from "./client.js";

export const EVENT_TYPES = ["plan", "tool_call", "observation", "section", "error", "done"];

/**
 * Subscribe to a run's SSE stream using the native EventSource.
 *
 * - Calls onEvent(name, data) for every contract event, in order.
 * - Closes itself after `done` or `error` (the stream ends there per the contract).
 * - If the connection drops before the run finished, calls onEvent("error", ...)
 *   once and closes. We deliberately do NOT let EventSource auto-reconnect, since a
 *   reconnect would replay the run from the start.
 *
 * @param {string} runId
 * @param {(name: string, data: any) => void} onEvent
 * @param {{ EventSourceImpl?: typeof EventSource }} [options]
 * @returns {() => void} close function (safe to call more than once)
 */
export function subscribeToRun(runId, onEvent, options = {}) {
  const ES = options.EventSourceImpl || globalThis.EventSource;
  if (!ES) {
    queueMicrotask(() =>
      onEvent("error", { message: "This browser does not support live streaming (EventSource)." })
    );
    return () => {};
  }

  const source = new ES(eventsUrl(runId));
  let closed = false;

  const close = () => {
    if (closed) return;
    closed = true;
    source.close();
  };

  const parse = (raw) => {
    try {
      return raw ? JSON.parse(raw) : {};
    } catch {
      return null;
    }
  };

  for (const type of EVENT_TYPES) {
    source.addEventListener(type, (e) => {
      if (closed) return;

      // A native connection failure also fires an "error" event, but without data.
      if (type === "error" && typeof e.data !== "string") {
        close();
        onEvent("error", { message: "Lost connection to the RepoPilot backend." });
        return;
      }

      const data = parse(e.data);
      if (data === null) return; // ignore malformed payloads rather than crash the run

      if (type === "done" || type === "error") close();
      onEvent(type, data);
    });
  }

  return close;
}
