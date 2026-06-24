"""Tavily provider (optional, requires TAVILY_API_KEY)."""
from __future__ import annotations

import httpx

from .search_providers import RawResult, SearchProvider


class TavilyProvider(SearchProvider):
    name = "tavily"
    endpoint = "https://api.tavily.com/search"

    def __init__(self, api_key: str, timeout: float = 20.0):
        self.api_key = api_key
        self.timeout = timeout

    def available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "TAVILY_API_KEY is not set."
        return True, ""

    def search(self, query: str, max_results: int = 8) -> list[RawResult]:
        ok, reason = self.available()
        if not ok:
            raise RuntimeError(reason)
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": "basic",
        }
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(self.endpoint, json=payload)
            r.raise_for_status()
            data = r.json()
        out = []
        for item in data.get("results", [])[:max_results]:
            out.append(
                RawResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    provider="tavily",
                    extra={"score": item.get("score")},
                )
            )
        return out
