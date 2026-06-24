import type {
  ChatResponse,
  EvalReport,
  IndexedFile,
  MemoryItem,
  Mode,
} from "./types";

// Default to the Next.js rewrite proxy (/api -> backend). Override with
// NEXT_PUBLIC_API_URL to point straight at the FastAPI server.
const BASE = process.env.NEXT_PUBLIC_API_URL || "/api";

async function jget<T>(path: string): Promise<T> {
  const r = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!r.ok) throw new Error(`GET ${path} failed: ${r.status}`);
  return r.json();
}

async function jsend<T>(path: string, method: string, body?: unknown): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    const detail = await r.text();
    throw new Error(`${method} ${path} failed: ${r.status} ${detail}`);
  }
  return r.json();
}

export interface HealthInfo {
  status: string;
  app: string;
  model: { ok: boolean; detail: string; provider: string };
  search: { provider: string; ok: boolean; detail: string };
  privacy: { local_privacy_mode: boolean; cloud_enabled: boolean; code_execution: boolean };
  embeddings: string;
  vector_store: string;
}

export const api = {
  health: () => jget<HealthInfo>("/health"),
  models: () => jget<{ provider: string; models: string[]; error?: string }>("/models"),

  chat: (payload: {
    message: string;
    history: { role: string; content: string }[];
    mode: Mode;
    use_web: boolean | null;
    local_privacy: boolean;
    file_ids: string[];
    settings?: { model?: string };
  }) => jsend<ChatResponse>("/chat", "POST", payload),

  // Memory
  listMemory: () => jget<MemoryItem[]>("/memory"),
  searchMemory: (q: string) => jget<MemoryItem[]>(`/memory/search?q=${encodeURIComponent(q)}`),
  createMemory: (m: { content: string; type: string; tags: string[]; importance: number }) =>
    jsend<MemoryItem>("/memory", "POST", { ...m, user_confirmed: true }),
  deleteMemory: (id: string) => jsend<{ deleted: string }>(`/memory/${id}`, "DELETE"),

  // Files
  listFiles: () => jget<{ files: IndexedFile[] }>("/files"),
  ingestFile: async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    const r = await fetch(`${BASE}/files/ingest`, { method: "POST", body: fd });
    if (!r.ok) throw new Error(`ingest failed: ${r.status} ${await r.text()}`);
    return r.json() as Promise<{ file_id: string; filename: string; num_chunks: number; injection_flagged: boolean }>;
  },
  deleteFile: (id: string) => jsend<{ deleted: string }>(`/files/${id}`, "DELETE"),

  // Evals
  runEvals: () => jsend<EvalReport>("/evals/run", "POST"),
  evalResults: () => jget<EvalReport>("/evals/results"),

  // Settings
  getSettings: () => jget<Record<string, unknown>>("/settings"),
  updateSettings: (updates: Record<string, unknown>) =>
    jsend<{ applied: Record<string, string> }>("/settings", "POST", { updates }),
};
