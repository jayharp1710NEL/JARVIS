"""Files API — ingest (upload), search/ask, list, delete."""
from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from ..rag.ingest import delete_indexed_file, ingest_bytes, list_indexed_files
from ..rag.loaders import UnsupportedFileType
from ..rag.retrieval import retrieve, to_citations

router = APIRouter(prefix="/files", tags=["files"])


@router.get("")
def list_files() -> dict:
    return {"files": list_indexed_files()}


@router.post("/ingest")
async def ingest(file: UploadFile = File(...)) -> dict:
    data = await file.read()
    try:
        result = ingest_bytes(file.filename or "upload.txt", data)
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"ingest failed: {exc}")
    return {
        "file_id": result.file_id,
        "filename": result.filename,
        "num_chunks": result.num_chunks,
        "injection_flagged": result.injection_flagged,
    }


class FileSearchBody(BaseModel):
    query: str
    top_k: int = 5
    file_ids: list[str] = []


@router.post("/search")
def search(body: FileSearchBody) -> dict:
    chunks = retrieve(body.query, body.top_k, body.file_ids or None)
    return {
        "chunks": [c.__dict__ for c in chunks],
        "citations": [c.model_dump() for c in to_citations(chunks)],
    }


@router.delete("/{file_id}")
def delete_file(file_id: str) -> dict:
    if not delete_indexed_file(file_id):
        raise HTTPException(status_code=404, detail="file not found in index")
    return {"deleted": file_id}
