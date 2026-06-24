"""Web search tests — exercise ranking/dedup/credibility without network."""
from app.web.credibility import classify, domain_of
from app.web.rank_sources import dedupe, rank
from app.web.search_providers import RawResult, get_search_provider


def _raw(title, url, snippet=""):
    return RawResult(title=title, url=url, snippet=snippet, provider="test")


def test_credibility_classification():
    assert classify("https://www.nih.gov/article")[0] == "official"
    assert classify("https://arxiv.org/abs/1234")[0] == "academic"
    assert classify("https://docs.python.org/3/")[0] == "documentation"
    assert classify("https://reddit.com/r/x")[0] == "forum"
    t, score = classify("https://some-random-shop.com")
    assert t == "commercial"
    assert 0 <= score <= 1


def test_domain_of():
    assert domain_of("https://www.example.com/path") == "example.com"


def test_dedupe_removes_duplicate_urls():
    results = [_raw("a", "https://x.com/p"), _raw("a2", "https://x.com/p#frag"), _raw("b", "https://y.com")]
    deduped = dedupe(results)
    urls = {r.url for r in deduped}
    assert "https://y.com" in urls
    assert len([r for r in deduped if "x.com" in r.url]) == 1


def test_rank_prefers_authoritative_and_relevant():
    results = [
        _raw("Python release notes", "https://docs.python.org/3/whatsnew", "python new features"),
        _raw("Random blog about python", "https://someone.medium.com/python", "python opinion"),
        _raw("Spam", "https://pinterest.com/pin/123", ""),
    ]
    ranked = rank("python new features", results)
    assert ranked[0].domain == "docs.python.org"
    # labels assigned
    assert ranked[0].citation_label.startswith("[1]")


def test_rank_caps_per_domain():
    results = [_raw(f"t{i}", f"https://x.com/{i}", "topic") for i in range(5)]
    ranked = rank("topic", results, max_per_domain=2)
    assert len(ranked) == 2


def test_search_provider_factory_defaults_searxng():
    sp = get_search_provider()
    assert sp.name in ("searxng", "none")
