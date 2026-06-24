"""File loaders — extract text + metadata from supported file types.

Heavy parsers (pypdf, python-docx) are imported lazily so the core does not
hard-depend on them. Unsupported types raise a clear error.
"""
from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass, field
from pathlib import Path

# Plain-text-ish extensions we read directly.
TEXT_EXTS = {
    ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css",
    ".java", ".cpp", ".c", ".h", ".rs", ".go", ".sql", ".sh", ".yaml",
    ".yml", ".toml", ".ini", ".log",
}
STRUCTURED_EXTS = {".json", ".csv"}
DOC_EXTS = {".pdf", ".docx"}
SUPPORTED_EXTS = TEXT_EXTS | STRUCTURED_EXTS | DOC_EXTS


class UnsupportedFileType(ValueError):
    pass


@dataclass
class LoadedPage:
    text: str
    page: int | None = None


@dataclass
class LoadedDoc:
    filename: str
    file_type: str
    pages: list[LoadedPage] = field(default_factory=list)
    bytes: int = 0

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages)


def _load_text(data: bytes) -> list[LoadedPage]:
    return [LoadedPage(text=data.decode("utf-8", errors="replace"))]


def _load_json(data: bytes) -> list[LoadedPage]:
    try:
        obj = json.loads(data.decode("utf-8", errors="replace"))
        pretty = json.dumps(obj, indent=2, ensure_ascii=False)
    except Exception:
        pretty = data.decode("utf-8", errors="replace")
    return [LoadedPage(text=pretty)]


def _load_csv(data: bytes) -> list[LoadedPage]:
    text = data.decode("utf-8", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return [LoadedPage(text="")]
    header = rows[0]
    lines = []
    for r in rows[1:]:
        pairs = [f"{h}: {v}" for h, v in zip(header, r)]
        lines.append("; ".join(pairs))
    body = "Columns: " + ", ".join(header) + "\n" + "\n".join(lines)
    return [LoadedPage(text=body)]


def _load_pdf(data: bytes) -> list[LoadedPage]:
    from pypdf import PdfReader  # lazy

    reader = PdfReader(io.BytesIO(data))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            txt = page.extract_text() or ""
        except Exception:
            txt = ""
        if txt.strip():
            pages.append(LoadedPage(text=txt, page=i))
    if not pages:
        pages = [LoadedPage(text="[no extractable text in PDF]", page=1)]
    return pages


def _load_docx(data: bytes) -> list[LoadedPage]:
    import docx  # python-docx, lazy

    doc = docx.Document(io.BytesIO(data))
    paras = [p.text for p in doc.paragraphs if p.text.strip()]
    return [LoadedPage(text="\n\n".join(paras))]


def load_bytes(filename: str, data: bytes) -> LoadedDoc:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTS:
        raise UnsupportedFileType(
            f"Unsupported file type '{ext}'. Supported: "
            + ", ".join(sorted(SUPPORTED_EXTS))
        )
    if ext in TEXT_EXTS:
        pages = _load_text(data)
    elif ext == ".json":
        pages = _load_json(data)
    elif ext == ".csv":
        pages = _load_csv(data)
    elif ext == ".pdf":
        pages = _load_pdf(data)
    elif ext == ".docx":
        pages = _load_docx(data)
    else:  # pragma: no cover
        raise UnsupportedFileType(ext)
    return LoadedDoc(filename=filename, file_type=ext.lstrip("."), pages=pages, bytes=len(data))


def load_path(path: str | Path) -> LoadedDoc:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {p}")
    return load_bytes(p.name, p.read_bytes())
