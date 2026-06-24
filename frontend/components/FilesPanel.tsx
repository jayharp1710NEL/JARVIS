"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { IndexedFile } from "@/lib/types";
import FileUpload from "./FileUpload";

interface Hit {
  text: string;
  filename: string;
  page: number | null;
  score: number;
  chunk_id: string;
}

export default function FilesPanel() {
  const [files, setFiles] = useState<IndexedFile[]>([]);
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<Hit[]>([]);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    try {
      const r = await api.listFiles();
      setFiles(r.files);
    } catch (e) {
      setErr(String(e));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function search() {
    if (!query.trim()) return;
    setErr(null);
    try {
      const r = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/files/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 6 }),
      });
      const data = await r.json();
      setHits(data.chunks || []);
    } catch (e) {
      setErr(String(e));
    }
  }

  async function remove(id: string) {
    await api.deleteFile(id);
    load();
  }

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <div>
        <FileUpload onIngested={load} />
        <h2 className="text-white font-medium mt-4 mb-2">Indexed files</h2>
        {files.length === 0 && <div className="text-muted text-sm">No files indexed yet.</div>}
        <div className="space-y-2">
          {files.map((f) => (
            <div
              key={f.id}
              className="rounded-lg border border-edge bg-card p-3 flex items-center justify-between"
            >
              <div>
                <div className="text-sm text-white">{f.filename}</div>
                <div className="text-xs text-muted">
                  {f.file_type} · {f.num_chunks} chunks · {(f.bytes / 1024).toFixed(1)} KB
                </div>
              </div>
              <button
                onClick={() => remove(f.id)}
                className="text-xs text-rose-300 hover:text-rose-200"
              >
                delete
              </button>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h2 className="text-white font-medium mb-2">Ask over files</h2>
        <div className="flex gap-2 mb-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && search()}
            placeholder="Search your documents…"
            className="flex-1 rounded-md border border-edge bg-card px-3 py-2 text-sm"
          />
          <button onClick={search} className="px-3 rounded-md border border-edge bg-card text-sm">
            Search
          </button>
        </div>
        {err && <div className="text-rose-300 text-sm mb-2">{err}</div>}
        <div className="space-y-2">
          {hits.map((h) => (
            <div key={h.chunk_id} className="rounded-lg border border-edge bg-panel p-3">
              <div className="text-xs text-muted mb-1">
                {h.filename}
                {h.page ? ` · p.${h.page}` : ""} · score {h.score.toFixed(2)}
              </div>
              <div className="text-sm text-[#d6d6db]">{h.text.slice(0, 400)}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
