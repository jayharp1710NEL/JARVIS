"""Brave Search provider (optional, requires BRAVE_API_KEY)."""
from __future__ import annotations

import httpx

from .search_providers import RawResult, SearchProvider


class BraveProvider(SearchProvider):
    name = "brave"
    endpoint = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, timeout: float = 20.0):
        self.api_key = api_key
        self.timeout = timeout

    def available(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "BRAVE_API_KEY is not set."
        return True, ""

    def search(self, query: str, max_results: int = 8) -> list[RawResult]:
        ok, reason = self.available()
        if not ok:
            raise RuntimeError(reason)
        headers = {"Accept": "application/json", "X-Subscription-Token": self.api_key}
        params = {"q": query, "count": max_results}
        with httpx.Client(timeout=self.timeout) as client:
            r = client.get(self.endpoint, headers=headers, params=params)
            r.raise_for_status()
            data = r.json()
        out = []
        for item in (data.get("web", {}) or {}).get("results", [])[:max_results]:
            out.append(
                RawResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    published_at=item.get("age"),
                    provider="brave",
                )
            )
        return out
