"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";

export default function FileUpload({
  onIngested,
  compact = false,
}: {
  onIngested?: (info: { file_id: string; filename: string; injection_flagged: boolean }) => void;
  compact?: boolean;
}) {
  const ref = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  async function handle(files: FileList | null) {
    if (!files || files.length === 0) return;
    setBusy(true);
    setMsg(null);
    try {
      for (const f of Array.from(files)) {
        const info = await api.ingestFile(f);
        onIngested?.(info);
        setMsg(
          `Indexed ${info.filename}` +
            (info.injection_flagged ? " ⚠ contained instruction-like text (treated as data)" : "")
        );
      }
    } catch (e) {
      setMsg(String(e));
    } finally {
      setBusy(false);
      if (ref.current) ref.current.value = "";
    }
  }

  return (
    <div className={compact ? "" : "rounded-lg border border-dashed border-edge p-4 bg-panel"}>
      <input
        ref={ref}
        type="file"
        multiple
        className="hidden"
        onChange={(e) => handle(e.target.files)}
      />
      <button
        onClick={() => ref.current?.click()}
        disabled={busy}
        className="px-3 py-1.5 rounded-md text-sm bg-card border border-edge text-white hover:border-accent/50 disabled:opacity-50"
      >
        {busy ? "Indexing…" : compact ? "📎 Attach" : "📎 Upload & index file"}
      </button>
      {msg && <div className="mt-2 text-xs text-muted">{msg}</div>}
    </div>
  );
}
