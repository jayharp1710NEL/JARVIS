export type Mode =
  | "fast"
  | "research"
  | "deep"
  | "builder"
  | "truth"
  | "debate"
  | "privacy"
  | "autopilot";

export type Confidence = "high" | "medium" | "low";

export interface Source {
  id: string;
  title: string;
  url: string;
  domain: string;
  snippet: string;
  published_at?: string | null;
  provider: string;
  credibility_score: number;
  source_type: string;
  citation_label: string;
}

export interface FileCitation {
  filename: string;
  page?: number | null;
  chunk_id: string;
  excerpt: string;
  score: number;
}

export interface ToolCallTrace {
  tool: string;
  input: Record<string, unknown>;
  ok: boolean;
  summary: string;
  error?: string | null;
  duration_ms: number;
}

export interface Claim {
  text: string;
  status: "verified" | "likely" | "uncertain" | "contradicted" | "speculative";
  support: string[];
  note: string;
}

export interface ChatResponse {
  answer: string;
  mode: Mode;
  sources: Source[];
  file_citations: FileCitation[];
  memory_used: string[];
  tool_trace: ToolCallTrace[];
  claims: Claim[];
  confidence: Confidence;
  uncertainty: string[];
  reasoning_summary: string;
  next_best_action: string;
  warnings: string[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}

export interface MemoryItem {
  id: string;
  type: string;
  content: string;
  tags: string[];
  importance: number;
  created_at: number;
  updated_at: number;
  source: string;
  user_confirmed: boolean;
  sensitive_flag: boolean;
}

export interface IndexedFile {
  id: string;
  filename: string;
  file_type: string;
  num_chunks: number;
  bytes: number;
  created_at: number;
}

export interface EvalOutcome {
  task_id: string;
  category: string;
  jarvis_score: number;
  baseline_score: number;
  delta: number;
  passed: boolean;
  web_allowed: boolean;
  reasons: string[];
}

export interface EvalReport {
  created_at: number;
  provider: string;
  model: string;
  offline_fake: boolean;
  search_available: boolean;
  outcomes: EvalOutcome[];
  jarvis_avg: number;
  baseline_avg: number;
  delta_avg: number;
  pass_rate: number;
  notes: string[];
}
