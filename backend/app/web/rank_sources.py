"""Deduplicate, score and rank search results into Source objects."""
from __future__ import annotations

import time
from urllib.parse import urlparse

from ..agent.schemas import Source
from .credibility import classify, domain_of
from .search_providers import RawResult

# Domains that are usually low-signal SEO/spam for research purposes.
_LOW_SIGNAL_HINTS = ("pinterest.", "answers.", "ezinearticles.", "/amp/")


def _spam_penalty(url: str, snippet: str) -> float:
    u = url.lower()
    penalty = 0.0
    if any(h in u for h in _LOW_SIGNAL_HINTS):
        penalty += 0.3
    if len(snippet) < 20:
        penalty += 0.05
    return penalty


def _relevance(query: str, r: RawResult) -> float:
    q_terms = {t for t in query.lower().split() if len(t) > 2}
    if not q_terms:
        return 0.5
    text = (r.title + " " + r.snippet).lower()
    hits = sum(1 for t in q_terms if t in text)
    return hits / len(q_terms)


def dedupe(results: list[RawResult]) -> list[RawResult]:
    seen_urls: set[str] = set()
    out: list[RawResult] = []
    for r in results:
        norm = r.url.split("#")[0].rstrip("/")
        if not norm or norm in seen_urls:
            continue
        seen_urls.add(norm)
        out.append(r)
    return out


def rank(
    query: str,
    results: list[RawResult],
    *,
    prefer_recent: bool = False,
    max_per_domain: int = 2,
) -> list[Source]:
    results = dedupe(results)
    scored: list[tuple[float, Source]] = []
    domain_counts: dict[str, int] = {}

    for i, r in enumerate(results):
        domain = domain_of(r.url) or urlparse(r.url).netloc
        source_type, cred = classify(r.url)
        relevance = _relevance(query, r)
        spam = _spam_penalty(r.url, r.snippet)

        score = (
            relevance * 0.45
            + cred * 0.35
            - spam
        )
        if r.published_at and prefer_recent:
            score += 0.1
        if source_type in ("official", "academic", "documentation"):
            score += 0.05  # primary-source bonus

        src = Source(
            id=f"S{i+1}",
            title=r.title or r.url,
            url=r.url,
            domain=domain,
            snippet=r.snippet,
            retrieved_at=time.time(),
            published_at=r.published_at,
            provider=r.provider,
            credibility_score=round(cred, 2),
            source_type=source_type,
        )
        scored.append((score, src))

    scored.sort(key=lambda t: t[0], reverse=True)

    final: list[Source] = []
    for _, src in scored:
        c = domain_counts.get(src.domain, 0)
        if c >= max_per_domain:
            continue
        domain_counts[src.domain] = c + 1
        final.append(src)

    # Re-label after final ordering so citation labels are stable & sequential.
    for idx, src in enumerate(final, start=1):
        src.id = f"S{idx}"
        src.citation_label = f"[{idx}] {src.domain}"
    return final
