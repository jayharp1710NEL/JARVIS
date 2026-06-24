"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { MemoryItem } from "@/lib/types";

const TYPES = [
  "user_preference",
  "project_fact",
  "long_term_goal",
  "repeated_instruction",
  "task_note",
  "personal_note",
  "technical_context",
  "writing_style_preference",
];

export default function MemoryPanel() {
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [query, setQuery] = useState("");
  const [content, setContent] = useState("");
  const [type, setType] = useState("task_note");
  const [tags, setTags] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    try {
      setItems(query.trim() ? await api.searchMemory(query) : await api.listMemory());
    } catch (e) {
      setErr(String(e));
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function add() {
    if (!content.trim()) return;
    try {
      await api.createMemory({
        content,
        type,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
        importance: 0.6,
      });
      setContent("");
      setTags("");
      load();
    } catch (e) {
      setErr(String(e));
    }
  }

  async function remove(id: string) {
    await api.deleteMemory(id);
    load();
  }

  return (
    <div className="grid md:grid-cols-3 gap-4">
      <div className="md:col-span-1 rounded-xl border border-edge bg-panel p-4 h-fit">
        <h2 className="text-white font-medium mb-3">Add memory</h2>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="e.g. User prefers concise, technical answers"
          rows={3}
          className="w-full rounded-md border border-edge bg-card px-3 py-2 text-sm mb-2"
        />
        <select
          value={type}
          onChange={(e) => setType(e.target.value)}
          className="w-full rounded-md border border-edge bg-card px-2 py-1.5 text-sm mb-2"
        >
          {TYPES.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <input
          value={tags}
          onChange={(e) => setTags(e.target.value)}
          placeholder="tags, comma, separated"
          className="w-full rounded-md border border-edge bg-card px-3 py-1.5 text-sm mb-2"
        />
        <button
          onClick={add}
          className="w-full rounded-md bg-accent/20 border border-accent/40 text-accent py-1.5 text-sm hover:bg-accent/30"
        >
          Save
        </button>
        <p className="text-xs text-muted mt-3">
          Memory is stored locally in SQLite and never sent to the cloud unless
          you explicitly enable it.
        </p>
      </div>

      <div className="md:col-span-2">
        <div className="flex gap-2 mb-3">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && load()}
            placeholder="Search memory…"
            className="flex-1 rounded-md border border-edge bg-card px-3 py-2 text-sm"
          />
          <button onClick={load} className="px-3 rounded-md border border-edge bg-card text-sm">
            Search
          </button>
        </div>
        {err && <div className="text-rose-300 text-sm mb-2">{err}</div>}
        <div className="space-y-2">
          {items.length === 0 && (
            <div className="text-muted text-sm">No memories yet.</div>
          )}
          {items.map((m) => (
            <div
              key={m.id}
              className="rounded-lg border border-edge bg-card p-3 flex items-start justify-between gap-3"
            >
              <div className="min-w-0">
                <div className="text-sm text-white">{m.content}</div>
                <div className="text-xs text-muted mt-1 flex flex-wrap gap-2">
                  <span className="px-1.5 rounded bg-panel border border-edge">{m.type}</span>
                  {m.tags.map((t) => (
                    <span key={t}>#{t}</span>
                  ))}
                  <span>imp {m.importance.toFixed(1)}</span>
                  {m.sensitive_flag && <span className="text-amber-300">sensitive</span>}
                </div>
              </div>
              <button
                onClick={() => remove(m.id)}
                className="text-xs text-rose-300 hover:text-rose-200 shrink-0"
              >
                delete
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
