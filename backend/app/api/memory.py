"""Memory API."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..memory.schemas import MemoryCreate, MemoryItem, MemoryUpdate
from ..memory.service import memory_service

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=list[MemoryItem])
def list_memory(limit: int = 200) -> list[MemoryItem]:
    return memory_service.list(limit)


@router.get("/search", response_model=list[MemoryItem])
def search_memory(q: str, top_k: int = 5) -> list[MemoryItem]:
    return [r.item for r in memory_service.search(q, top_k)]


@router.post("", response_model=MemoryItem)
def create_memory(data: MemoryCreate) -> MemoryItem:
    return memory_service.save(data)


@router.patch("/{mem_id}", response_model=MemoryItem)
def update_memory(mem_id: str, data: MemoryUpdate) -> MemoryItem:
    item = memory_service.update(mem_id, data)
    if not item:
        raise HTTPException(status_code=404, detail="memory not found")
    return item


@router.delete("/{mem_id}")
def delete_memory(mem_id: str) -> dict:
    if not memory_service.delete(mem_id):
        raise HTTPException(status_code=404, detail="memory not found")
    return {"deleted": mem_id}


@router.delete("")
def wipe_memory() -> dict:
    n = memory_service.wipe_all()
    return {"wiped": n}
