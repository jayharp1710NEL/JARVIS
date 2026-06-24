"""Ollama provider — the default local backend.

Talks to the Ollama HTTP API. Designed to give a *clear* error when Ollama
is not running or the model is not installed, instead of a raw connection
traceback.
"""
from __future__ import annotations

import json
from typing import Any, AsyncIterator

import httpx

from ..agent.schemas import Message
from .base import (
    GenSettings,
    HealthStatus,
    ModelError,
    ModelProvider,
    messages_to_dicts,
)


class OllamaProvider(ModelProvider):
    name = "ollama"

    def __init__(self, base_url: str, model: str, timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    # -- helpers ----------------------------------------------------------
    def _options(self, s: GenSettings) -> dict[str, Any]:
        opts: dict[str, Any] = {
            "temperature": s.temperature,
            "top_p": s.top_p,
            "num_predict": s.max_tokens,
        }
        if s.stop:
            opts["stop"] = s.stop
        opts.update(s.extra or {})
        return opts

    def _explain(self, exc: Exception) -> ModelError:
        if isinstance(exc, httpx.ConnectError):
            return ModelError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Is it running? Start it with `ollama serve` and pull a model "
                f"with `ollama pull {self.model}`."
            )
        if isinstance(exc, httpx.HTTPStatusError):
            body = exc.response.text[:300]
            if exc.response.status_code == 404:
                return ModelError(
                    f"Ollama model '{self.model}' not found (404). "
                    f"Pull it with `ollama pull {self.model}`. Detail: {body}"
                )
            return ModelError(
                f"Ollama returned HTTP {exc.response.status_code}: {body}"
            )
        return ModelError(f"Ollama request failed: {exc}")

    # -- interface --------------------------------------------------------
    def generate(self, messages: list[Message], settings: GenSettings) -> str:
        payload = {
            "model": self.model,
            "messages": messages_to_dicts(messages),
            "stream": False,
            "options": self._options(settings),
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(f"{self.base_url}/api/chat", json=payload)
                r.raise_for_status()
                data = r.json()
            return (data.get("message") or {}).get("content", "")
        except Exception as exc:  # noqa: BLE001
            raise self._explain(exc) from exc

    def generate_json(
        self, messages: list[Message], schema: dict | None, settings: GenSettings
    ) -> Any:
        payload = {
            "model": self.model,
            "messages": messages_to_dicts(messages),
            "stream": False,
            "format": "json",  # Ollama native JSON mode
            "options": self._options(settings),
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(f"{self.base_url}/api/chat", json=payload)
                r.raise_for_status()
                data = r.json()
            content = (data.get("message") or {}).get("content", "")
            return json.loads(content)
        except json.JSONDecodeError:
            # Fall back to robust extraction
            from .base import extract_json

            return extract_json(content)
        except Exception as exc:  # noqa: BLE001
            raise self._explain(exc) from exc

    async def stream(
        self, messages: list[Message], settings: GenSettings
    ) -> AsyncIterator[str]:
        payload = {
            "model": self.model,
            "messages": messages_to_dicts(messages),
            "stream": True,
            "options": self._options(settings),
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST", f"{self.base_url}/api/chat", json=payload
                ) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        piece = (chunk.get("message") or {}).get("content", "")
                        if piece:
                            yield piece
                        if chunk.get("done"):
                            break
        except Exception as exc:  # noqa: BLE001
            raise self._explain(exc) from exc

    def list_models(self) -> list[str]:
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(f"{self.base_url}/api/tags")
                r.raise_for_status()
                data = r.json()
            return [m["name"] for m in data.get("models", [])]
        except Exception as exc:  # noqa: BLE001
            raise self._explain(exc) from exc

    def health_check(self) -> HealthStatus:
        try:
            models = self.list_models()
            installed = self.model in models or any(
                m.split(":")[0] == self.model.split(":")[0] for m in models
            )
            if not installed:
                return HealthStatus(
                    ok=False,
                    provider=self.name,
                    detail=(
                        f"Ollama is running but model '{self.model}' is not "
                        f"installed. Run `ollama pull {self.model}`."
                    ),
                    models=models,
                )
            return HealthStatus(
                ok=True,
                provider=self.name,
                detail=f"Ollama reachable at {self.base_url}; model '{self.model}' ready.",
                models=models,
            )
        except ModelError as exc:
            return HealthStatus(ok=False, provider=self.name, detail=str(exc))
