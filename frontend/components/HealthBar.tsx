"use client";

import { useEffect, useState } from "react";
import { api, type HealthInfo } from "@/lib/api";

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${
        ok ? "bg-emerald-400" : "bg-rose-400"
      }`}
    />
  );
}

export default function HealthBar() {
  const [h, setH] = useState<HealthInfo | null>(null);
  const [err, setErr] = useState(false);

  useEffect(() => {
    api.health().then(setH).catch(() => setErr(true));
  }, []);

  if (err)
    return (
      <div className="text-xs text-rose-300 font-mono">
        backend unreachable — start it with <code>jarvis serve</code>
      </div>
    );
  if (!h) return <div className="text-xs text-muted">checking…</div>;

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-mono text-muted">
      <span className="flex items-center gap-1.5" title={h.model.detail}>
        <Dot ok={h.model.ok} /> model: {h.model.provider}
      </span>
      <span className="flex items-center gap-1.5" title={h.search.detail}>
        <Dot ok={h.search.ok} /> search: {h.search.provider}
      </span>
      <span className="flex items-center gap-1.5">
        <Dot ok={!h.privacy.cloud_enabled} />
        {h.privacy.cloud_enabled ? "cloud ON" : "local-only"}
      </span>
      {h.privacy.local_privacy_mode && (
        <span className="text-accent">🔒 privacy mode</span>
      )}
      <span>emb: {h.embeddings}</span>
      <span>vec: {h.vector_store}</span>
    </div>
  );
}
