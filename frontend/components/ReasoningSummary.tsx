"use client";

import { useState } from "react";
import type { ChatResponse } from "@/lib/types";

export default function ReasoningSummary({ resp }: { resp: ChatResponse }) {
  const [openTrace, setOpenTrace] = useState(false);
  const tools = resp.tool_trace ?? [];
  return (
    <div className="mt-3 rounded-lg border border-edge bg-panel p-3 text-sm">
      <div className="text-xs uppercase tracking-wider text-muted mb-1">
        Reasoning summary
      </div>
      <p className="text-[#cfcfd6]">{resp.reasoning_summary || "—"}</p>

      {resp.uncertainty?.length > 0 && (
        <div className="mt-2">
          <div className="text-xs uppercase tracking-wider text-amber-300/80 mb-1">
            Uncertainty
          </div>
          <ul className="list-disc list-inside text-amber-200/90 space-y-0.5">
            {resp.uncertainty.map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </div>
      )}

      {resp.next_best_action && (
        <div className="mt-2 text-accent">→ {resp.next_best_action}</div>
      )}

      {tools.length > 0 && (
        <div className="mt-2">
          <button
            onClick={() => setOpenTrace((v) => !v)}
            className="text-xs text-muted hover:text-white"
          >
            {openTrace ? "▼" : "▶"} Tool trace ({tools.length})
          </button>
          {openTrace && (
            <div className="mt-1 space-y-1 font-mono text-xs">
              {tools.map((t, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded border border-edge bg-card px-2 py-1"
                >
                  <span className={t.ok ? "text-emerald-300" : "text-rose-300"}>
                    {t.ok ? "✓" : "✗"} {t.tool}
                  </span>
                  <span className="text-muted truncate ml-2">
                    {t.summary || t.error} · {Math.round(t.duration_ms)}ms
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {resp.warnings?.map((w, i) => (
        <div key={i} className="mt-2 text-rose-300 text-xs">
          {w}
        </div>
      ))}
    </div>
  );
}
