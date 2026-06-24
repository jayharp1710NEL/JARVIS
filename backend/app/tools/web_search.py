"""web_search tool — search + dedupe + rank into Source objects."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..security.permissions import Permission
from ..web.rank_sources import rank
from ..web.search_providers import get_search_provider
from .base import Tool


class WebSearchInput(BaseModel):
    query: str = Field(..., description="Search query")
    max_results: int = Field(8, ge=1, le=20)
    prefer_recent: bool = False


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the web (SearxNG by default) and return ranked sources."
    permissions = [Permission.network_external]
    InputModel = WebSearchInput

    def execute(self, params: WebSearchInput):
        provider = get_search_provider()
        available, reason = provider.available()
        if not available:
            raise RuntimeError(reason)
        raw = provider.search(params.query, params.max_results)
        sources = rank(params.query, raw, prefer_recent=params.prefer_recent)
        data = [s.model_dump() for s in sources]
        return data, f"{len(sources)} ranked sources from {provider.name}"
