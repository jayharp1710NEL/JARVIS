"""Pytest fixtures: isolated temp data dir, offline by default, fresh state."""
from __future__ import annotations

import os
import tempfile

import pytest

# Configure a throwaway data dir and disable .env loading BEFORE app imports.
_TMP = tempfile.mkdtemp(prefix="jarvis-test-")
os.environ["JARVIS_ENV_FILE"] = "/dev/null"
os.environ["DATA_DIR"] = _TMP
os.environ["EMBEDDING_PROVIDER"] = "hashing"
os.environ["MODEL_PROVIDER"] = "ollama"


@pytest.fixture(autouse=True)
def _fresh_state():
    """Reset settings cache, DB engine and vector store between tests."""
    from app.config import reload_settings
    from app.memory.db import init_engine
    from app.rag.vector_store import reset_vector_store

    reload_settings()
    init_engine()
    reset_vector_store()
    # wipe persisted state
    from app.memory.service import memory_service

    memory_service.wipe_all()
    from app.rag.vector_store import get_vector_store

    get_vector_store().clear()
    yield


@pytest.fixture
def fake_provider():
    from app.models.fake import FakeProvider

    return FakeProvider()


@pytest.fixture
def orchestrator(fake_provider):
    from app.agent.orchestrator import AgentOrchestrator

    return AgentOrchestrator(provider=fake_provider)
