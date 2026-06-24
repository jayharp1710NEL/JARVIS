"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { EvalReport } from "@/lib/types";

function bar(score: number) {
  const pct = Math.round(score * 100);
  const color = pct >= 60 ? "bg-emerald-400/70" : pct >= 30 ? "bg-amber-400/70" : "bg-rose-400/70";
  return (
    <div className="h-1.5 w-24 rounded bg-edge overflow-hidden">
      <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function EvalDashboard() {
  const [report, setReport] = useState<EvalReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api.evalResults().then(setReport).catch(() => {});
  }, []);

  async function run() {
    setBusy(true);
    setErr(null);
    try {
      setReport(await api.runEvals());
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-4">
        <button
          onClick={run}
          disabled={busy}
          className="px-4 py-2 rounded-md bg-accent/20 border border-accent/40 text-accent hover:bg-accent/30 disabled:opacity-50"
        >
          {busy ? "Running…" : "Run evals"}
        </button>
        <p className="text-sm text-muted">
          Compares the full agent vs a raw-model baseline. Scores are honest:
          web/knowledge tasks score low without a model or search provider.
        </p>
      </div>

      {err && <div className="text-rose-300 text-sm mb-3">{err}</div>}

      {report && (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
            <Stat label="Jarvis avg" value={report.jarvis_avg.toFixed(2)} />
            <Stat label="Baseline avg" value={report.baseline_avg.toFixed(2)} />
            <Stat
              label="Δ (agent gain)"
              value={`${report.delta_avg >= 0 ? "+" : ""}${report.delta_avg.toFixed(2)}`}
              good={report.delta_avg > 0}
            />
            <Stat label="Pass rate" value={`${Math.round(report.pass_rate * 100)}%`} />
          </div>

          <div className="text-xs text-muted mb-3 font-mono">
            provider: {report.provider} · model: {report.model}
            {report.offline_fake && " · (offline fake model)"}
            {!report.search_available && " · (no search provider)"}
          </div>

          {report.notes.map((n, i) => (
            <div key={i} className="text-xs text-amber-200/90 mb-1">⚠ {n}</div>
          ))}

          <div className="mt-3 rounded-xl border border-edge overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-panel text-muted text-xs uppercase">
                <tr>
                  <th className="text-left px-3 py-2">Task</th>
                  <th className="text-left px-3 py-2">Category</th>
                  <th className="text-left px-3 py-2">Jarvis</th>
                  <th className="text-left px-3 py-2">Baseline</th>
                  <th className="text-left px-3 py-2">Δ</th>
                  <th className="px-3 py-2">Pass</th>
                </tr>
              </thead>
              <tbody>
                {report.outcomes.map((o) => (
                  <tr key={o.task_id} className="border-t border-edge">
                    <td className="px-3 py-2 font-mono text-xs">{o.task_id}</td>
                    <td className="px-3 py-2 text-muted">{o.category}</td>
                    <td className="px-3 py-2">{bar(o.jarvis_score)}</td>
                    <td className="px-3 py-2">{bar(o.baseline_score)}</td>
                    <td
                      className={`px-3 py-2 font-mono ${
                        o.delta > 0 ? "text-emerald-300" : o.delta < 0 ? "text-rose-300" : "text-muted"
                      }`}
                    >
                      {o.delta >= 0 ? "+" : ""}
                      {o.delta.toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-center">{o.passed ? "✅" : "❌"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}

function Stat({ label, value, good }: { label: string; value: string; good?: boolean }) {
  return (
    <div className="rounded-xl border border-edge bg-panel p-3">
      <div className="text-xs text-muted">{label}</div>
      <div className={`text-2xl font-mono ${good ? "text-emerald-300" : "text-white"}`}>
        {value}
      </div>
    </div>
  );
}
