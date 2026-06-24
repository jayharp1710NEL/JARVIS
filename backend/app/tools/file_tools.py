"""File tools: ingest local files and search/ask over the local index."""
from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from ..config import get_settings
from ..rag.ingest import ingest_path
from ..rag.retrieval import retrieve, to_citations
from ..security.permissions import Permission
from .base import Tool


def _within_workspace(path: Path) -> bool:
    settings = get_settings()
    try:
        path.resolve().relative_to(Path(settings.workspace_dir).resolve())
        return True
    except ValueError:
        # also allow uploads dir
        try:
            path.resolve().relative_to(Path(settings.uploads_dir).resolve())
            return True
        except ValueError:
            return False


class FileIngestInput(BaseModel):
    path: str = Field(..., description="Path to a local file inside the workspace")


class LocalFileIngestTool(Tool):
    name = "local_file_ingest"
    description = "Index a local file (txt/md/pdf/docx/csv/json/code) for retrieval."
    permissions = [Permission.read]
    InputModel = FileIngestInput

    def execute(self, params: FileIngestInput):
        p = Path(params.path)
        if not _within_workspace(p):
            raise PermissionError(
                f"Refusing to read '{p}': outside the allowed workspace "
                f"({get_settings().workspace_dir})."
            )
        res = ingest_path(p)
        return res.__dict__, f"indexed {res.filename} ({res.num_chunks} chunks)"


class FileSearchInput(BaseModel):
    query: str
    top_k: int = 5
    file_ids: list[str] = Field(default_factory=list)


class LocalFileSearchTool(Tool):
    name = "local_file_search"
    description = "Retrieve relevant chunks from indexed local files with citations."
    permissions = [Permission.read]
    InputModel = FileSearchInput

    def execute(self, params: FileSearchInput):
        chunks = retrieve(params.query, params.top_k, params.file_ids or None)
        cites = to_citations(chunks)
        data = {
            "chunks": [c.__dict__ for c in chunks],
            "citations": [c.model_dump() for c in cites],
        }
        return data, f"{len(chunks)} relevant chunks"
