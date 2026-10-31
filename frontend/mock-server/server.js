// Fake RepoPilot API for parallel frontend development. No dependencies.
// Implements the contract in docs/API_CONTRACT.md:
//   GET  /api/health
//   POST /api/runs
//   GET  /api/runs/:id/events   (SSE, replayed from fixtures/events.json)
//   GET  /api/runs/:id/report
//
// Test hooks (use as the repo name):
//   .../anything/notfound   -> 404 repo_not_found
//   .../anything/ratelimit  -> 429 rate_limited
//   .../anything/boom       -> run emits a fatal `error` event mid-stream
// Set SPEED=0.2 to play the run faster.

import http from "node:http";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { randomUUID } from "node:crypto";

const here = dirname(fileURLToPath(import.meta.url));
const events = JSON.parse(readFileSync(join(here, "fixtures/events.json"), "utf8"));
const report = JSON.parse(readFileSync(join(here, "fixtures/report.json"), "utf8"));

const PORT = Number(process.env.PORT || 8000);
const SPEED = Number(process.env.SPEED || 1);
const ORIGIN = process.env.FRONTEND_ORIGIN || "http://localhost:5173";

/** @type {Map<string, { repo: string, finished: boolean, boom: boolean }>} */
const runs = new Map();

const REPO_RE = /^https:\/\/github\.com\/([\w.-]+)\/([\w.-]+?)(?:\.git)?\/?$/;

function cors(res) {
  res.setHeader("Access-Control-Allow-Origin", ORIGIN);
  res.setHeader("Access-Control-Allow-Methods", "GET,POST,OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

function sendJson(res, status, body) {
  cors(res);
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

function sendError(res, status, code, message) {
  sendJson(res, status, { error: { code, message } });
}

function readBody(req) {
  return new Promise((resolve) => {
    let raw = "";
    req.on("data", (c) => (raw += c));
    req.on("end", () => {
      try {
        resolve(raw ? JSON.parse(raw) : {});
      } catch {
        resolve(null);
      }
    });
  });
}

function streamRun(req, res, runId) {
  const run = runs.get(runId);
  cors(res);
  res.writeHead(200, {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache",
    Connection: "keep-alive",
  });
  res.write(": connected\n\n");

  let closed = false;
  req.on("close", () => (closed = true));

  const script = run.boom
    ? [
        ...events.slice(0, 6),
        { delay: 800, event: "error", data: { message: "GitHub API rate limit hit while reading files." } },
      ]
    : events;

  let i = 0;
  const step = () => {
    if (closed) return;
    if (i >= script.length) return res.end();
    const { delay, event, data } = script[i++];
    setTimeout(() => {
      if (closed) return;
      res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
      if (event === "done") {
        run.finished = true;
        return res.end();
      }
      if (event === "error") return res.end();
      step();
    }, delay * SPEED);
  };
  step();
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const path = url.pathname;

  if (req.method === "OPTIONS") {
    cors(res);
    res.writeHead(204);
    return res.end();
  }

  if (req.method === "GET" && path === "/api/health") {
    return sendJson(res, 200, { status: "ok" });
  }

  if (req.method === "POST" && path === "/api/runs") {
    const body = await readBody(req);
    const match = body && typeof body.repo_url === "string" ? body.repo_url.match(REPO_RE) : null;
    if (!match) {
      return sendError(res, 400, "invalid_repo_url", "That doesn't look like a GitHub repo URL (https://github.com/owner/name).");
    }
    const name = match[2].toLowerCase();
    if (name === "notfound") return sendError(res, 404, "repo_not_found", "We couldn't find that repository. Is it public?");
    if (name === "ratelimit") return sendError(res, 429, "rate_limited", "GitHub rate limit reached. Try again in a minute.");

    const id = randomUUID().slice(0, 8);
    runs.set(id, { repo: `${match[1]}/${match[2]}`, finished: false, boom: name === "boom" });
    return sendJson(res, 201, { run_id: id });
  }

  const m = path.match(/^\/api\/runs\/([\w-]+)\/(events|report)$/);
  if (req.method === "GET" && m) {
    const [, id, kind] = m;
    const run = runs.get(id);
    if (!run) return sendError(res, 404, "run_not_found", "No run with that id.");
    if (kind === "events") return streamRun(req, res, id);
    if (!run.finished) return sendError(res, 409, "run_not_finished", "The run is still in progress.");
    return sendJson(res, 200, { ...report, repo: run.repo });
  }

  sendError(res, 404, "not_found", "Unknown route.");
});

server.listen(PORT, () => {
  console.log(`RepoPilot mock API on http://localhost:${PORT} (speed x${SPEED})`);
});
