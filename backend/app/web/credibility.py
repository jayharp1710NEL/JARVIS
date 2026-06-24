"""Heuristic source credibility & type classification.

Pure heuristics over the domain/URL — no network calls. Not a ground-truth
authority score; it is a transparent prior that the ranker uses and that the
agent surfaces so the user can judge for themselves.
"""
from __future__ import annotations

from urllib.parse import urlparse

from ..agent.schemas import SourceType

_OFFICIAL_TLDS = (".gov", ".gov.uk", ".mil", ".int", ".europa.eu")
_ACADEMIC_TLDS = (".edu", ".ac.uk", ".edu.au")
_ACADEMIC_DOMAINS = {
    "arxiv.org", "nature.com", "science.org", "ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov",
    "jstor.org", "springer.com", "sciencedirect.com", "ieee.org", "acm.org",
    "semanticscholar.org", "researchgate.net", "plos.org",
}
_DOC_DOMAINS = {
    "docs.python.org", "developer.mozilla.org", "readthedocs.io", "kubernetes.io",
    "docs.djangoproject.com", "docs.aws.amazon.com", "learn.microsoft.com",
    "pkg.go.dev", "doc.rust-lang.org", "nodejs.org",
}
_NEWS_DOMAINS = {
    "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "nytimes.com",
    "theguardian.com", "wsj.com", "bloomberg.com", "ft.com", "npr.org",
    "economist.com", "washingtonpost.com",
}
_FORUM_DOMAINS = {
    "reddit.com", "stackoverflow.com", "stackexchange.com", "news.ycombinator.com",
    "quora.com", "discourse.org",
}
_BLOG_HINTS = ("medium.com", "substack.com", "blogspot.com", "wordpress.com", "dev.to")
_REFERENCE_DOMAINS = {"wikipedia.org", "britannica.com"}


def domain_of(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _matches(domain: str, collection) -> bool:
    return any(domain == d or domain.endswith("." + d) for d in collection)


def classify(url: str) -> tuple[SourceType, float]:
    """Return (source_type, credibility_score in 0..1)."""
    domain = domain_of(url)
    if not domain:
        return "unknown", 0.3

    if domain.endswith(_OFFICIAL_TLDS):
        return "official", 0.95
    if domain.endswith(_ACADEMIC_TLDS) or _matches(domain, _ACADEMIC_DOMAINS):
        return "academic", 0.9
    if _matches(domain, _DOC_DOMAINS) or domain.startswith("docs."):
        return "documentation", 0.85
    if _matches(domain, _REFERENCE_DOMAINS):
        return "documentation", 0.75
    if _matches(domain, _NEWS_DOMAINS):
        return "news", 0.75
    if _matches(domain, _FORUM_DOMAINS):
        return "forum", 0.5
    if any(h in domain for h in _BLOG_HINTS):
        return "blog", 0.45
    if domain.endswith(".org"):
        return "official", 0.65
    if domain.endswith((".com", ".io", ".net", ".co")):
        return "commercial", 0.5
    return "unknown", 0.4
