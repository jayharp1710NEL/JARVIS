"""OpenAI-compatible local provider.

Works with LM Studio, llama.cpp server, vLLM, text-generation-webui and any
other server exposing the ``/v1/chat/completions`` API. The base URL points
at a *local* endpoint by default.
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
    extract_json,
    messages_to_dicts,
)


class OpenAICompatibleProvider(ModelProvider):
    name = "openai_compatible"

    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str = "not-needed",
        timeout: float = 120.0,
        provider_name: str = "openai_compatible",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self.name = provider_name

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def _body(self, messages: list[Message], s: GenSettings, stream: bool) -> dict[str, Any]:
        body = {
            "model": self.model,
            "messages": messages_to_dicts(messages),
            "temperature": s.temperature,
            "top_p": s.top_p,
            "max_tokens": s.max_tokens,
            "stream": stream,
        }
        if s.stop:
            body["stop"] = s.stop
        body.update(s.extra or {})
        return body

    def _explain(self, exc: Exception) -> ModelError:
        if isinstance(exc, httpx.ConnectError):
            return ModelError(
                f"Could not connect to the OpenAI-compatible endpoint at "
                f"{self.base_url}. Make sure your local server (LM Studio / "
                "llama.cpp / vLLM) is running and the base URL is correct."
            )
        if isinstance(exc, httpx.HTTPStatusError):
            return ModelError(
                f"Endpoint returned HTTP {exc.response.status_code}: "
                f"{exc.response.text[:300]}"
            )
        return ModelError(f"Request to {self.base_url} failed: {exc}")

    def generate(self, messages: list[Message], settings: GenSettings) -> str:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=self._body(messages, settings, stream=False),
                )
                r.raise_for_status()
                data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception as exc:  # noqa: BLE001
            raise self._explain(exc) from exc

    def generate_json(
        self, messages: list[Message], schema: dict | None, settings: GenSettings
    ) -> Any:
        body = self._body(messages, settings, stream=False)
        body["response_format"] = {"type": "json_object"}
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=body,
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"]
            return extract_json(content)
        except httpx.HTTPStatusError:
            # Some servers reject response_format; retry without it.
            raw = self.generate(messages, settings)
            return extract_json(raw)
        except Exception as exc:  # noqa: BLE001
            raise self._explain(exc) from exc

    async def stream(
        self, messages: list[Message], settings: GenSettings
    ) -> AsyncIterator[str]:
        body = self._body(messages, settings, stream=True)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._headers(),
                    json=body,
                ) as r:
                    r.raise_for_status()
                    async for line in r.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[len("data:") :].strip()
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
                        if delta:
                            yield delta
        except Exception as exc:  # noqa: BLE001
            raise self._explain(exc) from exc

    def list_models(self) -> list[str]:
        try:
            with httpx.Client(timeout=10.0) as client:
                r = client.get(f"{self.base_url}/models", headers=self._headers())
                r.raise_for_status()
                data = r.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception as exc:  # noqa: BLE001
            raise self._explain(exc) from exc

    def health_check(self) -> HealthStatus:
        try:
            models = self.list_models()
            return HealthStatus(
                ok=True,
                provider=self.name,
                detail=f"Endpoint reachable at {self.base_url}.",
                models=models,
            )
        except ModelError as exc:
            return HealthStatus(ok=False, provider=self.name, detail=str(exc))
