"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Settings = Record<string, any>;

export default function SettingsPanel() {
  const [s, setS] = useState<Settings | null>(null);
  const [draft, setDraft] = useState<Settings>({});
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    api.getSettings().then((d) => {
      setS(d);
      setDraft(d);
    });
  }, []);

  function set(key: string, value: any) {
    setDraft((d) => ({ ...d, [key]: value }));
  }

  async function save() {
    setMsg(null);
    const updates: Settings = {};
    const keys = [
      "model_provider",
      "ollama_base_url",
      "ollama_model",
      "openai_base_url",
      "openai_model",
      "search_provider",
      "searxng_url",
      "embedding_provider",
      "vector_store",
      "temperature",
      "max_tokens",
      "local_privacy_mode",
      "enable_cloud_mode",
      "allow_private_data_to_cloud",
      "allow_code_execution",
    ];
    for (const k of keys) if (s && draft[k] !== s[k]) updates[k] = draft[k];
    if (Object.keys(updates).length === 0) {
      setMsg("No changes.");
      return;
    }
    try {
      const r = await api.updateSettings(updates);
      setMsg(`Applied: ${Object.keys(r.applied).join(", ")}`);
      const fresh = await api.getSettings();
      setS(fresh);
      setDraft(fresh);
    } catch (e) {
      setMsg(String(e));
    }
  }

  if (!s) return <div className="text-muted">Loading settings…</div>;

  const Field = ({ k, label }: { k: string; label: string }) => (
    <label className="block">
      <span className="text-xs text-muted">{label}</span>
      <input
        value={draft[k] ?? ""}
        onChange={(e) => set(k, e.target.value)}
        className="w-full rounded-md border border-edge bg-card px-3 py-1.5 text-sm mt-1"
      />
    </label>
  );

  const Toggle = ({ k, label, danger }: { k: string; label: string; danger?: boolean }) => (
    <label className="flex items-center justify-between rounded-md border border-edge bg-card px-3 py-2">
      <span className={`text-sm ${danger ? "text-amber-300" : "text-white"}`}>{label}</span>
      <input
        type="checkbox"
        checked={!!draft[k]}
        onChange={(e) => set(k, e.target.checked)}
        className="accent-cyan-400"
      />
    </label>
  );

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <section className="rounded-xl border border-edge bg-panel p-4 space-y-3">
        <h2 className="text-white font-medium">Model</h2>
        <Field k="model_provider" label="Provider (ollama | openai_compatible | cloud)" />
        <Field k="ollama_base_url" label="Ollama base URL" />
        <Field k="ollama_model" label="Ollama model" />
        <Field k="openai_base_url" label="OpenAI-compatible base URL" />
        <Field k="openai_model" label="OpenAI-compatible model" />
        <Field k="temperature" label="Temperature" />
        <Field k="max_tokens" label="Max tokens" />
      </section>

      <section className="rounded-xl border border-edge bg-panel p-4 space-y-3">
        <h2 className="text-white font-medium">Search & RAG</h2>
        <Field k="search_provider" label="Search provider (searxng | brave | tavily | serper | none)" />
        <Field k="searxng_url" label="SearxNG URL" />
        <Field k="embedding_provider" label="Embeddings (hashing | sentence_transformers | ollama)" />
        <Field k="vector_store" label="Vector store (numpy | chroma)" />

        <h2 className="text-white font-medium pt-2">Privacy & safety</h2>
        <Toggle k="local_privacy_mode" label="Local privacy mode (block all egress)" />
        <Toggle k="enable_cloud_mode" label="Enable cloud model (sends data out)" danger />
        <Toggle k="allow_private_data_to_cloud" label="Allow private data to cloud" danger />
        <Toggle k="allow_code_execution" label="Allow sandboxed code execution" danger />
      </section>

      <div className="md:col-span-2 flex items-center gap-3">
        <button
          onClick={save}
          className="px-4 py-2 rounded-md bg-accent/20 border border-accent/40 text-accent hover:bg-accent/30"
        >
          Save settings
        </button>
        {msg && <span className="text-sm text-muted">{msg}</span>}
      </div>
    </div>
  );
}
