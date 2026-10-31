import { Component, useEffect, useRef, useState } from "react";
import { cleanMermaid } from "../lib/report.js";
import { SpinnerIcon } from "./icons.jsx";

// Mermaid is large, so load it on demand and only once.
let mermaidPromise = null;
function loadMermaid() {
  if (!mermaidPromise) {
    mermaidPromise = import("mermaid").then((mod) => {
      const mermaid = mod.default;
      mermaid.initialize({
        startOnLoad: false,
        theme: "dark",
        securityLevel: "strict",
        suppressErrorRendering: true,
        fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif",
      });
      return mermaid;
    });
    mermaidPromise.catch(() => {
      mermaidPromise = null; // allow a retry if the chunk failed to load
    });
  }
  return mermaidPromise;
}

let diagramCounter = 0;

/** LLM-written Mermaid can be invalid, so we always have a readable fallback. */
function RawSource({ source, note }) {
  return (
    <div>
      <p className="mb-2 text-xs text-amber-200/90">{note}</p>
      <pre className="overflow-x-auto rounded-xl border border-white/10 bg-ink-900 p-3 font-mono text-xs text-slate-300">
        {source}
      </pre>
    </div>
  );
}

function DiagramInner({ source }) {
  const containerRef = useRef(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error

  useEffect(() => {
    let cancelled = false;
    const id = `mmd-${++diagramCounter}`;
    setStatus("loading");

    loadMermaid()
      .then((mermaid) => mermaid.render(id, source))
      .then(({ svg }) => {
        if (cancelled || !containerRef.current) return;
        containerRef.current.innerHTML = svg;
        setStatus("ready");
      })
      .catch(() => {
        document.getElementById(`d${id}`)?.remove(); // mermaid can leave a stray node behind
        if (!cancelled) setStatus("error");
      });

    return () => {
      cancelled = true;
    };
  }, [source]);

  return (
    <>
      {status === "loading" && (
        <p className="flex items-center gap-2 text-sm text-slate-400">
          <SpinnerIcon /> Rendering diagram…
        </p>
      )}
      {status === "error" && (
        <RawSource source={source} note="Couldn't render this diagram, so here is its source instead." />
      )}
      <div
        ref={containerRef}
        data-testid="mermaid-output"
        className={`mermaid-wrap overflow-x-auto ${status === "ready" ? "" : "hidden"}`}
      />
    </>
  );
}

class DiagramBoundary extends Component {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return <RawSource source={this.props.source} note="Couldn't render this diagram, so here is its source instead." />;
    }
    return this.props.children;
  }
}

export default function MermaidDiagram({ source }) {
  const cleaned = cleanMermaid(source);
  if (!cleaned) {
    return <p className="text-sm text-slate-400">The agent didn't produce a diagram for this repo.</p>;
  }
  return (
    <DiagramBoundary key={cleaned} source={cleaned}>
      <DiagramInner source={cleaned} />
    </DiagramBoundary>
  );
}
