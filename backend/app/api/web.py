"""Web API — search and read-url."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..web.extract import read_url
from ..web.rank_sources import rank
from ..web.search_providers import get_search_provider

router = APIRouter(prefix="/web", tags=["web"])


class SearchBody(BaseModel):
    query: str
    max_results: int = 8
    prefer_recent: bool = False


@router.post("/search")
def web_search(body: SearchBody) -> dict:
    provider = get_search_provider()
    ok, reason = provider.available()
    if not ok:
        raise HTTPException(status_code=503, detail=reason)
    try:
        raw = provider.search(body.query, body.max_results)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc))
    sources = rank(body.query, raw, prefer_recent=body.prefer_recent)
    return {"provider": provider.name, "sources": [s.model_dump() for s in sources]}


class ReadUrlBody(BaseModel):
    url: str
    max_chars: int = 12000


@router.post("/read-url")
def web_read_url(body: ReadUrlBody) -> dict:
    res = read_url(body.url, body.max_chars)
    if not res.ok:
        raise HTTPException(status_code=502, detail=res.error or "read failed")
    return {
        "url": res.final_url,
        "title": res.title,
        "text": res.text,
        "excerpt": res.excerpt,
        "published_at": res.published_at,
        "truncated": res.truncated,
        "injection_risk": res.injection.level,
        "injection_tags": res.injection.tags,
    }
