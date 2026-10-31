import { useCallback, useEffect, useReducer, useRef } from "react";
import { createRun, getReport } from "../api/client.js";
import { subscribeToRun } from "../api/events.js";
import { validateRepoUrl } from "../lib/validators.js";
import { initialState, runReducer } from "./runReducer.js";

export { initialState, runReducer };

/**
 * Drives a run: create it, stream its events into the reducer, fetch the report on `done`.
 * @returns {{ state: typeof initialState, start: (repoUrl: string) => Promise<void>, retry: () => void, reset: () => void }}
 */
export function useRun() {
  const [state, dispatch] = useReducer(runReducer, initialState);
  const closeRef = useRef(null);
  const tokenRef = useRef(0); // bumped on every start/reset so stale callbacks are ignored
  const repoUrlRef = useRef("");

  const stopStream = useCallback(() => {
    if (closeRef.current) {
      closeRef.current();
      closeRef.current = null;
    }
  }, []);

  const start = useCallback(
    async (rawUrl) => {
      const check = validateRepoUrl(rawUrl);
      stopStream();
      const token = ++tokenRef.current;
      repoUrlRef.current = check.valid ? check.url : String(rawUrl ?? "");

      dispatch({ type: "START", repoUrl: repoUrlRef.current });

      if (!check.valid) {
        dispatch({ type: "FAIL", message: check.error });
        return;
      }

      try {
        const { run_id: runId } = await createRun(check.url);
        if (token !== tokenRef.current) return;
        dispatch({ type: "RUN_CREATED", runId });

        closeRef.current = subscribeToRun(runId, (name, data) => {
          if (token !== tokenRef.current) return;
          dispatch({ type: "EVENT", name, data });

          if (name === "done") {
            getReport(runId)
              .then((report) => {
                if (token === tokenRef.current) dispatch({ type: "REPORT_LOADED", report });
              })
              .catch((err) => {
                if (token === tokenRef.current) dispatch({ type: "FAIL", message: err.message });
              });
          }
        });
      } catch (err) {
        if (token === tokenRef.current) dispatch({ type: "FAIL", message: err.message });
      }
    },
    [stopStream]
  );

  const retry = useCallback(() => {
    if (repoUrlRef.current) start(repoUrlRef.current);
  }, [start]);

  const reset = useCallback(() => {
    tokenRef.current += 1;
    stopStream();
    repoUrlRef.current = "";
    dispatch({ type: "RESET" });
  }, [stopStream]);

  // Close the stream when the component unmounts.
  useEffect(() => () => stopStream(), [stopStream]);

  return { state, start, retry, reset };
}
