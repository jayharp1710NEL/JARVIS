"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function ModelSelector({
  model,
  onChange,
}: {
  model: string;
  onChange: (m: string) => void;
}) {
  const [models, setModels] = useState<string[]>([]);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    api
      .models()
      .then((r) => {
        setModels(r.models || []);
        if (r.error) setErr(r.error);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-muted">model</span>
      {models.length > 0 ? (
        <select
          value={model}
          onChange={(e) => onChange(e.target.value)}
          className="bg-card border border-edge rounded-md px-2 py-1 text-xs text-white"
        >
          <option value="">default</option>
          {models.map((m) => (
            <option key={m} value={m}>
              {m}
            </option>
          ))}
        </select>
      ) : (
        <span className="text-xs text-muted italic" title={err || ""}>
          {err ? "provider offline" : "loading…"}
        </span>
      )}
    </div>
  );
}
