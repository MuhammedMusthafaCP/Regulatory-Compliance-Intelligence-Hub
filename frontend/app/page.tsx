"use client";

import { useState } from "react";

type HealthResponse = {
  api_status: string;
  database_status: string;
  write_verified: boolean;
  read_verified: boolean;
  vector_support_verified: boolean;
  latest_record: {
    id: number;
    status: string;
    test_vector: number[];
    created_at: string;
  };
  checked_at: string;
};

type DiagnosticState =
  | { phase: "idle" }
  | { phase: "loading" }
  | { phase: "success"; data: HealthResponse; durationMs: number }
  | { phase: "error"; message: string };

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:7001";

export default function DashboardPage() {
  const [state, setState] = useState<DiagnosticState>({ phase: "idle" });

  async function runDiagnostic() {
    setState({ phase: "loading" });
    const startedAt = performance.now();
    try {
      const res = await fetch(`${API_URL}/api/health`, { cache: "no-store" });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail ?? `Request failed with status ${res.status}`);
      }
      const data: HealthResponse = await res.json();
      setState({ phase: "success", data, durationMs: performance.now() - startedAt });
    } catch (err) {
      setState({
        phase: "error",
        message:
          err instanceof Error
            ? err.message
            : "Unable to reach the processing engine. The database may be waking up — please retry in a few seconds.",
      });
    }
  }

  const isLoading = state.phase === "loading";

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-12">
      <div className="mx-auto max-w-3xl">
        <header className="mb-10">
          <p className="text-sm font-medium uppercase tracking-wider text-indigo-400">
            Phase 1 — Core Infrastructure & System Connectivity
          </p>
          <h1 className="mt-2 text-3xl font-semibold text-white">
            Regulatory &amp; Compliance Intelligence Hub
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">
            Executive operational dashboard verifying end-to-end connectivity
            across the user interface, application processing engine, and
            secure compliance data registry — the foundation for future
            grounded regulatory verification workflows.
          </p>
        </header>

        <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 shadow-lg">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-medium text-white">System Status</h2>
              <p className="mt-1 text-sm text-slate-400">
                Trigger a live diagnostic to confirm database read/write and
                vector indexing support.
              </p>
            </div>
            <StatusBadge state={state} />
          </div>

          <button
            onClick={runDiagnostic}
            disabled={isLoading}
            className="mt-6 inline-flex items-center justify-center rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isLoading ? "Running Diagnostic…" : "Test Full Stack Connection"}
          </button>

          {isLoading && (
            <p className="mt-3 text-xs text-amber-400">
              Waking up storage engine and validating connectivity — this may
              take a moment if the database is idle.
            </p>
          )}

          {state.phase === "error" && (
            <p className="mt-4 rounded-lg border border-red-900 bg-red-950/50 px-4 py-3 text-sm text-red-300">
              {state.message}
            </p>
          )}

          {state.phase === "success" && (
            <div className="mt-6">
              <p className="mb-2 text-xs text-slate-500">
                Verified in {Math.round(state.durationMs)} ms
              </p>
              <pre className="max-h-80 overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-4 text-xs leading-5 text-emerald-300">
                {JSON.stringify(state.data, null, 2)}
              </pre>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}

function StatusBadge({ state }: { state: DiagnosticState }) {
  const map: Record<DiagnosticState["phase"], { label: string; className: string }> = {
    idle: { label: "Not Checked", className: "bg-slate-800 text-slate-300" },
    loading: { label: "Checking…", className: "bg-amber-900/60 text-amber-300" },
    success: { label: "Operational", className: "bg-emerald-900/60 text-emerald-300" },
    error: { label: "Unavailable", className: "bg-red-900/60 text-red-300" },
  };
  const { label, className } = map[state.phase];
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-medium ${className}`}>
      {label}
    </span>
  );
}
