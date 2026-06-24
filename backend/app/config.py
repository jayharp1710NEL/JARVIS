"""Central configuration for JARVIS-LOCAL.

All configuration is environment-driven with safe, local-first defaults.
Nothing here reaches the cloud unless the user explicitly opts in.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository / data roots -------------------------------------------------
BACKEND_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = BACKEND_ROOT / "data"


class Settings(BaseSettings):
    """Runtime settings.

    Loaded from environment variables and an optional ``.env`` file. The
    defaults are deliberately local-only so the system is private out of the
    box.
    """

    model_config = SettingsConfigDict(
        env_file=os.environ.get("JARVIS_ENV_FILE", ".env"),
        env_prefix="",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- General ----
    app_name: str = "JARVIS-LOCAL"
    environment: Literal["dev", "prod", "test"] = Field(default="dev")
    data_dir: Path = Field(default=DEFAULT_DATA_DIR)
    log_level: str = Field(default="INFO")

    # ---- Model providers ----
    # The default provider used by the model router.
    model_provider: Literal["ollama", "openai_compatible", "cloud"] = "ollama"

    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.1:8b")

    # OpenAI-compatible local endpoint (LM Studio, llama.cpp server, vLLM...)
    openai_base_url: str = Field(default="http://localhost:1234/v1")
    openai_api_key: str = Field(default="not-needed")
    openai_model: str = Field(default="local-model")

    # Embeddings
    embedding_provider: Literal["hashing", "sentence_transformers", "ollama"] = "hashing"
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_dim: int = Field(default=384)

    # Generation defaults
    temperature: float = Field(default=0.7)
    top_p: float = Field(default=0.9)
    max_tokens: int = Field(default=1024)
    context_window: int = Field(default=8192)
    request_timeout: float = Field(default=120.0)

    # ---- Cloud (OFF by default) ----
    enable_cloud_mode: bool = Field(default=False)
    cloud_base_url: str = Field(default="https://api.openai.com/v1")
    cloud_api_key: str = Field(default="")
    cloud_model: str = Field(default="gpt-4o-mini")
    # Even when cloud is enabled, private data (files/memory) stays local
    # unless the user explicitly allows it.
    allow_private_data_to_cloud: bool = Field(default=False)

    # ---- Web search ----
    search_provider: Literal["searxng", "brave", "tavily", "serper", "none"] = "searxng"
    searxng_url: str = Field(default="http://localhost:8080")
    brave_api_key: str = Field(default="")
    tavily_api_key: str = Field(default="")
    serper_api_key: str = Field(default="")
    web_fetch_timeout: float = Field(default=20.0)
    web_max_results: int = Field(default=8)
    web_user_agent: str = Field(
        default="JARVIS-LOCAL/0.1 (+local research agent; respectful crawler)"
    )

    # ---- RAG / vector store ----
    vector_store: Literal["numpy", "chroma"] = "numpy"
    chunk_size: int = Field(default=900)
    chunk_overlap: int = Field(default=150)
    rag_top_k: int = Field(default=5)

    # ---- Security / privacy ----
    # Hard switch: when True the system refuses ALL outbound non-local calls.
    local_privacy_mode: bool = Field(default=False)
    allow_code_execution: bool = Field(default=False)
    # Folder the agent may read files from (file tools are sandboxed to this).
    workspace_dir: Path = Field(default=DEFAULT_DATA_DIR / "workspace")

    # ---- API ----
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    cors_origins: str = Field(default="http://localhost:3000")

    # ---- Derived paths ----------------------------------------------------
    @property
    def db_path(self) -> Path:
        return self.data_dir / "jarvis.db"

    @property
    def vector_dir(self) -> Path:
        return self.data_dir / "vectors"

    @property
    def eval_reports_dir(self) -> Path:
        return self.data_dir / "eval_reports"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def ensure_dirs(self) -> None:
        for p in (
            self.data_dir,
            self.vector_dir,
            self.eval_reports_dir,
            self.uploads_dir,
            self.workspace_dir,
        ):
            Path(p).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.ensure_dirs()
    return s


def reload_settings() -> Settings:
    """Clear the cache and reload (used after the settings API mutates env)."""
    get_settings.cache_clear()
    return get_settings()
