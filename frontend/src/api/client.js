const API_BASE = (import.meta.env?.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/+$/, "");

/** Error carrying the contract's error code (see docs/API_CONTRACT.md, 6.4). */
export class ApiError extends Error {
  /**
   * @param {string} code e.g. "invalid_repo_url", "network_error"
   * @param {string} message human-readable
   * @param {number} [status] HTTP status, 0 when the server was unreachable
   */
  constructor(code, message, status = 0) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

async function request(path, options) {
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, options);
  } catch {
    throw new ApiError(
      "network_error",
      "Can't reach the RepoPilot backend. Check that it is running and try again.",
      0
    );
  }

  let body = null;
  try {
    body = await res.json();
  } catch {
    // non-JSON body; handled below
  }

  if (!res.ok) {
    const err = body && body.error;
    throw new ApiError(
      (err && err.code) || "unknown_error",
      (err && err.message) || `Request failed with status ${res.status}.`,
      res.status
    );
  }
  return body;
}

/** GET /api/health */
export function health() {
  return request("/api/health");
}

/**
 * POST /api/runs
 * @param {string} repoUrl
 * @returns {Promise<{ run_id: string }>}
 */
export function createRun(repoUrl) {
  return request("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ repo_url: repoUrl }),
  });
}

/**
 * GET /api/runs/{id}/report
 * @param {string} runId
 */
export function getReport(runId) {
  return request(`/api/runs/${encodeURIComponent(runId)}/report`);
}

/** URL of the SSE stream for a run. */
export function eventsUrl(runId) {
  return `${API_BASE}/api/runs/${encodeURIComponent(runId)}/events`;
}
