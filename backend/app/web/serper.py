"""Serper.dev provider (optional, requires SERPER_API_KEY)."""
from __future__ import annotations

import httpx

from .search_providers import RawResult, SearchProvider


class SerperProvider(SearchProvider):
    name = "serper"
    endpoint = "https://google.serper.dev/search"

    def __init__(self, api_key: str, timeout: float = 20.0):
        self.api_key = api_key
        self.timeout = timeout

    def available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "SERPER_API_KEY is not set."
        return True, ""

    def search(self, query: str, max_results: int = 8) -> list[RawResult]:
        ok, reason = self.available()
        if not ok:
            raise RuntimeError(reason)
        headers = {"X-API-KEY": self.api_key, "Content-Type": "application/json"}
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(self.endpoint, headers=headers, json={"q": query, "num": max_results})
            r.raise_for_status()
            data = r.json()
        out = []
        for item in data.get("organic", [])[:max_results]:
            out.append(
                RawResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    published_at=item.get("date"),
                    provider="serper",
                )
            )
        return out
