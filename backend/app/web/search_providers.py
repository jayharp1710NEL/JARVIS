"""Web search provider abstraction + factory.

SearxNG (local, private) is the default. Brave / Tavily / Serper are optional
and only used when their API keys are configured. The privacy guard can block
external providers entirely.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..config import Settings, get_settings
from ..security.privacy import PrivacyGuard


@dataclass
class RawResult:
    title: str
    url: str
    snippet: str = ""
    published_at: str | None = None
    provider: str = "unknown"
    engine: str = ""
    extra: dict = field(default_factory=dict)


class SearchProvider(ABC):
    name = "base"

    @abstractmethod
    def search(self, query: str, max_results: int = 8) -> list[RawResult]: ...

    def available(self) -> tuple[bool, str]:
        """Return (is_available, reason_if_not)."""
        return True, ""


def get_search_provider(settings: Settings | None = None) -> SearchProvider:
    settings = settings or get_settings()
    guard = PrivacyGuard(settings)
    provider = settings.search_provider

    if provider == "none":
        return NullProvider("disabled by configuration")

    # In privacy mode only the local SearxNG instance is permitted.
    if settings.local_privacy_mode and provider != "searxng":
        return NullProvider(
            "Local Privacy Mode is ON — external search providers are blocked. "
            "Use a local SearxNG instance."
        )

    if provider == "searxng":
        from .searxng import SearxNGProvider

        return SearxNGProvider(settings.searxng_url, settings.web_fetch_timeout, guard)
    if provider == "brave":
        from .brave import BraveProvider

        return BraveProvider(settings.brave_api_key, settings.web_fetch_timeout)
    if provider == "tavily":
        from .tavily import TavilyProvider

        return TavilyProvider(settings.tavily_api_key, settings.web_fetch_timeout)
    if provider == "serper":
        from .serper import SerperProvider

        return SerperProvider(settings.serper_api_key, settings.web_fetch_timeout)
    return NullProvider(f"Unknown search provider '{provider}'")


class NullProvider(SearchProvider):
    name = "none"

    def __init__(self, reason: str):
        self.reason = reason

    def search(self, query: str, max_results: int = 8) -> list[RawResult]:
        return []

    def available(self) -> tuple[bool, str]:
        return False, self.reason
