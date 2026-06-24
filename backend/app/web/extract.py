"""read_url — fetch a page and extract clean main content.

Extraction strategy (best available, all optional):
  1. trafilatura (best) if installed
  2. BeautifulSoup readability-ish fallback (always available)
PDF URLs are detected and parsed with pypdf.

All fetched content is treated as UNTRUSTED and scanned for prompt injection.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field

import httpx

from ..config import get_settings
from ..security.privacy import PrivacyGuard
from ..security.prompt_injection import InjectionScan, scan


@dataclass
class ReadResult:
    url: str
    final_url: str
    title: str
    text: str
    excerpt: str
    published_at: str | None = None
    content_type: str = ""
    ok: bool = True
    error: str | None = None
    injection: InjectionScan = field(default_factory=InjectionScan)
    truncated: bool = False


_DATE_META = [
    re.compile(r'"datePublished"\s*:\s*"([^"]+)"'),
    re.compile(r'property="article:published_time"\s+content="([^"]+)"'),
    re.compile(r'name="date"\s+content="([^"]+)"'),
]


def _find_date(html: str) -> str | None:
    for rx in _DATE_META:
        m = rx.search(html)
        if m:
            return m.group(1)
    return None


def _extract_with_trafilatura(html: str, url: str) -> tuple[str, str] | None:
    try:
        import trafilatura  # lazy/optional

        text = trafilatura.extract(
            html, url=url, include_comments=False, include_tables=True
        )
        if text and text.strip():
            md = trafilatura.metadata.extract_metadata(html)
            title = (md.title if md else "") or ""
            return title, text.strip()
    except Exception:
        return None
    return None


def _extract_with_bs4(html: str) -> tuple[str, str]:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        tag.decompose()
    # Prefer <article> / <main> if present
    container = soup.find("article") or soup.find("main") or soup.body or soup
    text = container.get_text("\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return title, text


def _parse_pdf(data: bytes) -> tuple[str, str]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    parts = []
    for page in reader.pages:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return "", "\n\n".join(parts).strip()


def read_url(url: str, max_chars: int = 12000) -> ReadResult:
    settings = get_settings()
    guard = PrivacyGuard(settings)
    try:
        guard.check_outbound(url, purpose="read url")
    except Exception as exc:  # PrivacyViolation
        return ReadResult(url=url, final_url=url, title="", text="", excerpt="",
                          ok=False, error=str(exc))

    if not re.match(r"^https?://", url):
        return ReadResult(url=url, final_url=url, title="", text="", excerpt="",
                          ok=False, error="Only http(s) URLs are supported.")

    headers = {"User-Agent": settings.web_user_agent}
    try:
        with httpx.Client(timeout=settings.web_fetch_timeout, follow_redirects=True) as client:
            r = client.get(url, headers=headers)
            r.raise_for_status()
            content_type = r.headers.get("content-type", "")
            final_url = str(r.url)
            raw = r.content
    except httpx.HTTPStatusError as exc:
        return ReadResult(url=url, final_url=url, title="", text="", excerpt="",
                          ok=False, error=f"HTTP {exc.response.status_code} fetching page.")
    except httpx.ConnectError:
        return ReadResult(url=url, final_url=url, title="", text="", excerpt="",
                          ok=False, error="Could not connect to host.")
    except Exception as exc:  # noqa: BLE001
        return ReadResult(url=url, final_url=url, title="", text="", excerpt="",
                          ok=False, error=f"Fetch failed: {exc}")

    published = None
    if "application/pdf" in content_type or url.lower().endswith(".pdf"):
        try:
            title, text = _parse_pdf(raw)
        except Exception as exc:  # noqa: BLE001
            return ReadResult(url=url, final_url=final_url, title="", text="", excerpt="",
                              ok=False, error=f"PDF parse failed: {exc}")
    else:
        html = raw.decode("utf-8", errors="replace")
        published = _find_date(html)
        extracted = _extract_with_trafilatura(html, final_url)
        if extracted:
            title, text = extracted
        else:
            title, text = _extract_with_bs4(html)

    if not text.strip():
        return ReadResult(url=url, final_url=final_url, title=title, text="", excerpt="",
                          ok=False, error="No readable content could be extracted.")

    truncated = len(text) > max_chars
    text = text[:max_chars]
    injection = scan(text)
    excerpt = re.sub(r"\s+", " ", text)[:500]
    return ReadResult(
        url=url,
        final_url=final_url,
        title=title or final_url,
        text=text,
        excerpt=excerpt,
        published_at=published,
        content_type=content_type,
        ok=True,
        injection=injection,
        truncated=truncated,
    )
