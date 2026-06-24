"""FastAPI application entrypoint for JARVIS-LOCAL."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, evals, files, health, memory, settings as settings_api, web
from .api.settings import load_runtime_overrides
from .config import get_settings, reload_settings
from .memory.db import init_engine


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Apply persisted runtime overrides, then (re)load settings & DB.
    load_runtime_overrides()
    settings = reload_settings()
    settings.ensure_dirs()
    configure_logging(settings.log_level)
    init_engine()
    logging.getLogger("jarvis").info(
        "JARVIS-LOCAL started (provider=%s, search=%s, privacy=%s)",
        settings.model_provider, settings.search_provider, settings.local_privacy_mode,
    )
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="JARVIS-LOCAL",
        description="Local-first, private, tool-using AI agent operating layer.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(memory.router)
    app.include_router(files.router)
    app.include_router(web.router)
    app.include_router(evals.router)
    app.include_router(settings_api.router)

    @app.get("/")
    def root() -> dict:
        return {"app": "JARVIS-LOCAL", "docs": "/docs", "health": "/health"}

    return app


app = create_app()
