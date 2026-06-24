"use client";

import { useRef, useState } from "react";
import { api } from "@/lib/api";
import type { ChatMessage, Mode } from "@/lib/types";
import Message from "./Message";
import ModeSelector from "./ModeSelector";
import ModelSelector from "./ModelSelector";
import FileUpload from "./FileUpload";
import HealthBar from "./HealthBar";

export default function Chat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<Mode>("fast");
  const [model, setModel] = useState("");
  const [useWeb, setUseWeb] = useState<boolean | null>(null);
  const [privacy, setPrivacy] = useState(false);
  const [fileIds, setFileIds] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  async function send() {
    const text = input.trim();
    if (!text || busy) return;
    setError(null);
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    const next = [...messages, { role: "user" as const, content: text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const resp = await api.chat({
        message: text,
        history,
        mode,
        use_web: useWeb,
        local_privacy: privacy,
        file_ids: fileIds,
        settings: model ? { model } : undefined,
      });
      setMessages([...next, { role: "assistant", content: resp.answer, response: resp }]);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  return (
    <div className="grid grid-cols-1 gap-4">
      <div className="rounded-xl border border-edge bg-panel p-3 flex flex-col gap-3">
        <HealthBar />
        <ModeSelector mode={mode} onChange={setMode} />
        <div className="flex flex-wrap items-center gap-3">
          <ModelSelector model={model} onChange={setModel} />
          <label className="flex items-center gap-1.5 text-xs text-muted cursor-pointer">
            <input
              type="checkbox"
              checked={useWeb === true}
              onChange={(e) => setUseWeb(e.target.checked ? true : null)}
              className="accent-cyan-400"
            />
            web search
          </label>
          <label className="flex items-center gap-1.5 text-xs text-muted cursor-pointer">
            <input
              type="checkbox"
              checked={privacy}
              onChange={(e) => setPrivacy(e.target.checked)}
              className="accent-cyan-400"
            />
            local privacy
          </label>
          <FileUpload
            compact
            onIngested={(info) => setFileIds((ids) => [...ids, info.file_id])}
          />
          {fileIds.length > 0 && (
            <span className="text-xs text-accent">{fileIds.length} file(s) attached</span>
          )}
        </div>
      </div>

      <div className="rounded-xl border border-edge bg-ink min-h-[50vh] p-4 flex flex-col gap-4">
        {messages.length === 0 && (
          <div className="text-muted text-sm m-auto text-center max-w-md">
            <p className="text-white mb-1">Ask anything.</p>
            <p>
              JARVIS-LOCAL plans, uses tools, researches the web, reads your files
              and verifies before answering — all locally.
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <Message key={i} msg={m} />
        ))}
        {busy && <div className="text-accent text-sm animate-pulse">working…</div>}
        {error && (
          <div className="text-rose-300 text-sm border border-rose-500/30 rounded p-2 bg-rose-500/10">
            {error}
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send();
            }
          }}
          rows={2}
          placeholder="Message JARVIS-LOCAL…  (Enter to send, Shift+Enter for newline)"
          className="flex-1 resize-none rounded-xl border border-edge bg-card px-4 py-3 text-sm text-white focus:outline-none focus:border-accent/50"
        />
        <button
          onClick={send}
          disabled={busy}
          className="px-5 rounded-xl bg-accent/20 border border-accent/40 text-accent font-medium hover:bg-accent/30 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
