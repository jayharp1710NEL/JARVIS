# JARVIS-LOCAL

**A local-first, private, tool-using AI agent operating layer.**

JARVIS-LOCAL is not "one AI model." It is an operating layer *around* models,
tools, memory, research and evaluation. It runs on your machine by default,
keeps your data private by default, and is engineered to beat ordinary chatbot
usage on **practical workflows** through tools, web research, retrieval,
verification and self-critique.

> **Honesty first.** This system does **not** turn a small local model into a
> frontier model. A 7B model is still a 7B model. What an agent layer *can* do
> is make that model far more useful in practice — by giving it a calculator,
> your files, the live web, persistent memory, source comparison, and a
> verify-then-revise loop. The built-in eval lab measures this honestly and
> tells you when the agent is **not** better than a plain baseline.

---

## Table of contents
- [What it is / isn't](#what-it-is--isnt)
- [Privacy model](#privacy-model)
- [Architecture](#architecture)
- [Quick start](#quick-start)
- [Installing Ollama + a model](#installing-ollama--a-model)
- [SearxNG (private web search)](#searxng-private-web-search)
- [Running the backend](#running-the-backend)
- [Running the frontend](#running-the-frontend)
- [CLI usage](#cli-usage)
- [Web research](#web-research)
- [Memory](#memory)
- [File RAG](#file-rag)
- [Evals](#evals)
- [Docker](#docker)
- [Recommended local models & hardware](#recommended-local-models--hardware)
- [Extending the system](#extending-the-system)
- [Troubleshooting](#troubleshooting)
- [Safety notes](#safety-notes)

---

## What it is / isn't

**It is:**
- Local by default (Ollama or any OpenAI-compatible local server).
- Private by default (no cloud calls unless you explicitly enable them).
- Modular — swap models, tools, vector stores, search providers, UI.
- Tool-using, web-aware, file-aware, memory-aware.
- Benchmark-tested and self-correcting (verify → critique → revise).
- Honest about uncertainty (confidence + uncertainty on every answer).

**It is not:**
- A magic model that is "smarter than GPT/Claude/Gemini."
- A fake-AGI demo. Every module contains working code and tests.
- A thin wrapper that secretly phones home. It doesn't.

## Privacy model

- **Default:** everything stays on your machine. The model is local, the
  vector store is local, memory is a local SQLite file, and web search goes to
  a **local** SearxNG instance.
- **Cloud is OFF by default.** The cloud provider only exists if you set
  `ENABLE_CLOUD_MODE=true` *and* provide a key. Even then, your **files and
  memory are never sent to the cloud** unless you also set
  `ALLOW_PRIVATE_DATA_TO_CLOUD=true`.
- **Local Privacy Mode** (`LOCAL_PRIVACY_MODE=true`, or the UI toggle, or
  `jarvis ... --privacy`) hard-blocks *all* non-local network egress.
- **Untrusted content defense:** web pages and files are treated as **data,
  never instructions**. Indirect prompt-injection attempts are detected,
  neutralized (wrapped as data), flagged to you, and never executed.
- **No secret logging.** Secrets are never written to logs or returned by the
  settings API.

## Architecture

```
                 ┌──────────────────────── User (Web UI / CLI) ───────────────────────┐
                 │                                                                     │
                 ▼                                                                     │
        ┌──────────────────┐                                                          │
        │  Agent Kernel    │   classify → decide context → plan → execute            │
        │ (orchestrator)   │   → verify → critique → revise → compose                 │
        └───────┬──────────┘                                                          │
   ┌────────────┼─────────────┬───────────────┬───────────────┬──────────────┐       │
   ▼            ▼             ▼               ▼               ▼              ▼       │
┌───────┐ ┌──────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────┐    │
│ Model │ │  Tool    │ │  Research  │ │   Local    │ │  Memory    │ │ Verify / │    │
│Gateway│ │ Runtime  │ │  Engine    │ │ Knowledge  │ │  Engine    │ │ Critic   │    │
│Ollama │ │14 tools  │ │SearxNG +   │ │ (file RAG) │ │ (SQLite)   │ │ Engine   │    │
│/OpenAI│ │perms+    │ │read_url +  │ │numpy vec + │ │            │ │ground+   │    │
│-compat│ │sandbox   │ │rank+cite   │ │embeddings  │ │            │ │self-crit │    │
└───────┘ └──────────┘ └────────────┘ └────────────┘ └────────────┘ └──────────┘    │
                 │                                                                    │
                 ▼                                                                    │
        ┌──────────────────┐         ┌──────────────────┐                            │
        │  Security Layer  │         │     Eval Lab     │  Jarvis vs baseline ───────┘
        │ injection/privacy│         │ honest scoring   │
        │ /permissions     │         │ + regressions    │
        └──────────────────┘         └──────────────────┘
```

Backend modules live in `backend/app/`: `agent/`, `models/`, `tools/`, `web/`,
`memory/`, `rag/`, `evals/`, `security/`, `api/`, `cli/`. The frontend
(`frontend/`) is a Next.js + Tailwind UI.

## Quick start

```bash
# 0) clone, then:
cp .env.example .env            # local-first defaults; edit if you like

# 1) backend
cd backend
python3 -m pip install -r requirements.txt
python3 -m pytest -q            # 67 tests should pass (no model needed)
python3 -m uvicorn app.main:app --reload --port 8000

# 2) frontend (new terminal)
cd frontend
npm install
npm run dev                     # http://localhost:3000

# 3) a local model (new terminal) — see next section
ollama serve
ollama pull llama3.1:8b
```

Open <http://localhost:3000>. The health bar shows whether the model and
search provider are reachable. Without a model the system still runs and
returns a clear setup message instead of crashing.

## Windows one-click start

1. **Double-click `START_JARVIS.bat`** in the project root. It checks/install
   dependencies (into `backend\.venv` and `frontend\node_modules`), starts the
   backend + frontend (and SearxNG if Docker is running), waits for them, and
   opens <http://localhost:3000>.
2. **Install Ollama** from <https://ollama.com> and pull a model
   (`ollama pull llama3.1:8b`) — otherwise chat shows a setup message. The
   launcher warns you if Ollama isn't running but continues.
3. **Logs** are written to the `logs\` folder (`launcher.log`, `backend.log`,
   `frontend.log`). The two server windows stay open so you can see errors.
4. **If it fails:** read the message in the window / `logs\launcher.log`, fix
   the reported issue (install Python 3.10+ or Node LTS, free port 8000/3000,
   start Docker), and double-click again. To stop everything, double-click
   **`STOP_JARVIS.bat`**.

## Installing Ollama + a model

1. Install Ollama: <https://ollama.com/download>
2. Start it: `ollama serve` (listens on `http://localhost:11434`)
3. Pull a model: `ollama pull llama3.1:8b`
   (or `qwen2.5:7b`, `mistral:7b`, `llama3.2:3b`, `phi3:mini` …)
4. Point JARVIS at it: set `OLLAMA_MODEL` in `.env` (default `llama3.1:8b`).

**Using LM Studio / llama.cpp / vLLM instead?** Set
`MODEL_PROVIDER=openai_compatible` and `OPENAI_BASE_URL` to your server's
`/v1` endpoint.

## SearxNG (private web search)

Web research defaults to a **local** SearxNG instance.

```bash
docker run -d --name searxng -p 8080:8080 \
  -v "$(pwd)/searxng:/etc/searxng" searxng/searxng:latest
```

The bundled `searxng/settings.yml` already enables the **JSON** format that the
agent needs (`formats: [html, json]`). Set `SEARXNG_URL` if you run it
elsewhere.

**Optional external providers** (used only if you set the key):
`SEARCH_PROVIDER=brave|tavily|serper` with `BRAVE_API_KEY` / `TAVILY_API_KEY` /
`SERPER_API_KEY`.

## Running the backend

```bash
cd backend
python3 -m uvicorn app.main:app --reload --port 8000   # or: jarvis serve
```
Interactive API docs at <http://localhost:8000/docs>. Key endpoints:
`GET /health`, `GET /models`, `POST /chat`, `POST /chat/stream`,
`POST /web/search`, `POST /web/read-url`, `GET/POST/DELETE /memory`,
`POST /files/ingest`, `POST /files/search`, `POST /evals/run`,
`GET/POST /settings`.

## Running the frontend

```bash
cd frontend
npm run dev      # dev (http://localhost:3000)
# or
npm run build && npm run start
```
The UI proxies `/api/*` to the backend (configurable via `BACKEND_URL`).

Pages: **Chat** (modes, model/web/privacy toggles, file upload, sources,
reasoning summary, confidence, uncertainty, tool trace), **Memory**, **Files**,
**Evals**, **Settings**.

## CLI usage

The CLI is `jarvis` (after `pip install -e backend`) or
`python3 -m app.cli.main` from `backend/`.

```bash
jarvis ask "Explain RAG in two sentences"
jarvis research "latest stable Python release features"
jarvis deep "Design a rate limiter for a multi-tenant API"
jarvis truth "Are local LLMs as good as frontier models?"
jarvis ingest ./notes.pdf
jarvis files search "vector store"
jarvis memory save "I prefer concise, technical answers" --tags style
jarvis memory list
jarvis eval run
jarvis models
jarvis settings
jarvis serve
jarvis chat        # interactive
```

## Web research

In **Research** mode (or with the web toggle), the pipeline:
generates multiple angled queries → searches → dedupes → ranks by relevance,
credibility, recency and primary-source status → reads the best pages
(`read_url`, untrusted) → builds an injection-neutralized evidence block →
drafts with inline `[n]` citations → verifies groundedness → reports
disagreements and uncertainty. Sources are shown with type and a transparent
credibility prior. It never cites a source it didn't actually use.

## Memory

Local SQLite memory with typed entries (preferences, project facts, goals,
notes, technical context, writing style…). Save/search/list/update/delete via
UI, CLI, API, or the agent's `memory_*` tools. Memory used in an answer is
listed in the reasoning summary. Sensitive items can be flagged; memory never
leaves your machine unless you explicitly allow it.

## File RAG

Ingest `txt, md, pdf, docx, csv, json, py, js, ts, tsx, html, css, java, cpp,
c, rs, go, sql`. Files are chunked, embedded locally and stored in a numpy
vector store. Ask over them and get citations (`filename`, page, chunk id,
excerpt). The default **hashing embedder** needs no downloads; switch
`EMBEDDING_PROVIDER=sentence_transformers` for higher-quality semantic search.

## Evals

```bash
jarvis eval run            # or: python -m app.evals.runner run, or POST /evals/run
```
The lab runs a benchmark across 12 categories (factual QA, current web
research, citation quality, source comparison, math, coding, file RAG, memory
recall, prompt-injection resistance, uncertainty honesty, safety, tool
selection) and prints **Jarvis vs a raw-model baseline** with deltas,
pass/fail, regressions vs the previous run, and improvement suggestions.
Scoring is rule-based and reproducible — **no fake scores**. When no model or
search provider is available, the report says so and scores honestly (e.g.
web-research tasks score low without SearxNG).

## Docker

```bash
make docker-up      # backend + frontend + searxng
make docker-down
```
Ollama is expected to run on the **host** (so it can use your GPU); the backend
reaches it via `host.docker.internal`.

## Recommended local models & hardware

| Model | RAM/VRAM (approx) | Good for |
|---|---|---|
| `llama3.2:3b`, `phi3:mini` | 4–6 GB | fast chat, low-end machines |
| `llama3.1:8b`, `qwen2.5:7b`, `mistral:7b` | 8–12 GB | balanced default |
| `qwen2.5:14b`, `gemma2:9b` | 12–24 GB | stronger reasoning/coding |
| `llama3.1:70b` (quantized) | 40 GB+ | best local quality |

Tips: prefer quantized GGUF builds; close other GPU apps; lower `MAX_TOKENS`
and `CONTEXT_WINDOW` if you hit OOM; the hashing embedder + numpy vector store
are CPU-only and light.

## Extending the system

- **Add a tool:** subclass `tools/base.py:Tool`, declare an `InputModel` +
  permissions, register it in `tools/registry.py`. It's automatically traced
  and permission-checked.
- **Add a model provider:** implement `models/base.py:ModelProvider` and wire it
  in `models/router.py`.
- **Swap the vector store:** implement `rag/vector_store.py:VectorStore`
  (a Chroma adapter slot already exists).
- **Add a search provider:** implement `web/search_providers.py:SearchProvider`.
- **Add an eval:** append an `EvalTask` in `evals/tasks.py` with a `Rubric`.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Chat returns "couldn't complete… model" | Start `ollama serve` and `ollama pull <model>`; check `GET /health`. |
| `/models` empty / provider offline | Ollama not running, or wrong `OLLAMA_BASE_URL`. |
| Web search returns nothing | Start SearxNG and ensure `formats` includes `json`; or set a search API key. |
| `read_url` fails | Site blocked the request or returned no main content; try another source. |
| "Local Privacy Mode is ON" errors | Expected — privacy mode blocks external calls. Disable it to go online. |
| Unsupported file type | See the supported list above; convert first. |
| Frontend can't reach backend | Backend not running, or set `BACKEND_URL`/`NEXT_PUBLIC_API_URL`. |
| Worse-quality embeddings | Switch `EMBEDDING_PROVIDER=sentence_transformers` (downloads a model). |

## Safety notes

- **Code execution is OFF by default.** `safe_code_runner` only runs when
  `ALLOW_CODE_EXECUTION=true`, in an isolated subprocess with a timeout and a
  static blocklist. This is a guard rail for *your own* snippets, **not** a
  hardened sandbox for hostile code — don't run untrusted code through it.
- **Medical / legal / financial** answers include a caution and recommend a
  professional. This is general information, not professional advice.
- **Prompt injection** from pages/files is detected and treated as data, but no
  filter is perfect — review actions on sensitive tasks.

---

*Build the strongest real local Jarvis — no fake intelligence, no fake
benchmarks, no fake "done."*
