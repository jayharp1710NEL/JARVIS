"""SearxNG provider — local, private metasearch (the default)."""
from __future__ import annotations

import httpx

from ..security.privacy import PrivacyGuard
from .search_providers import RawResult, SearchProvider


class SearxNGProvider(SearchProvider):
    name = "searxng"

    def __init__(self, base_url: str, timeout: float, guard: PrivacyGuard):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.guard = guard

    def search(self, query: str, max_results: int = 8) -> list[RawResult]:
        # SearxNG is typically local; this passes the privacy guard.
        self.guard.check_outbound(self.base_url, purpose="web search")
        params = {
            "q": query,
            "format": "json",
            "safesearch": 1,
            "language": "en",
        }
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.get(f"{self.base_url}/search", params=params)
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"SearxNG returned HTTP {exc.response.status_code}. Ensure the "
                "JSON format is enabled in searxng settings.yml "
                "(formats: [html, json])."
            ) from exc
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"Could not reach SearxNG at {self.base_url}. Start it (see "
                "docker-compose) or set SEARCH_PROVIDER appropriately."
            ) from exc

        out: list[RawResult] = []
        for item in data.get("results", [])[:max_results]:
            out.append(
                RawResult(
                    title=item.get("title", "") or item.get("url", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    published_at=item.get("publishedDate"),
                    provider="searxng",
                    engine=item.get("engine", ""),
                )
            )
        return out

    def available(self) -> tuple[bool, str]:
        try:
            self.guard.check_outbound(self.base_url, purpose="web search")
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)
        return True, ""
