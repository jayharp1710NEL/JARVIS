"""Memory tools: save / search / list / delete."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..memory.schemas import MemoryCreate, MemoryType
from ..memory.service import memory_service
from ..security.permissions import Permission
from .base import Tool


class MemorySaveInput(BaseModel):
    content: str
    type: MemoryType = MemoryType.task_note
    tags: list[str] = Field(default_factory=list)
    importance: float = 0.5
    sensitive: bool = False
    source: str = "agent"


class MemorySaveTool(Tool):
    name = "memory_save"
    description = "Persist a useful, non-sensitive fact/preference to local memory."
    permissions = [Permission.memory_write]
    InputModel = MemorySaveInput

    def execute(self, params: MemorySaveInput):
        item = memory_service.save(
            MemoryCreate(
                content=params.content,
                type=params.type,
                tags=params.tags,
                importance=params.importance,
                sensitive_flag=params.sensitive,
                source=params.source,
                user_confirmed=False,
            )
        )
        return item.model_dump(), f"saved memory {item.id}"


class MemorySearchInput(BaseModel):
    query: str
    top_k: int = 5


class MemorySearchTool(Tool):
    name = "memory_search"
    description = "Search local memory for relevant preferences/facts/notes."
    permissions = [Permission.read]
    InputModel = MemorySearchInput

    def execute(self, params: MemorySearchInput):
        results = memory_service.search(params.query, params.top_k)
        data = [{"item": r.item.model_dump(), "score": r.score} for r in results]
        return data, f"{len(results)} memory matches"


class MemoryListInput(BaseModel):
    limit: int = 100


class MemoryListTool(Tool):
    name = "memory_list"
    description = "List stored memories."
    permissions = [Permission.read]
    InputModel = MemoryListInput

    def execute(self, params: MemoryListInput):
        items = memory_service.list(params.limit)
        return [i.model_dump() for i in items], f"{len(items)} memories"


class MemoryDeleteInput(BaseModel):
    id: str


class MemoryDeleteTool(Tool):
    name = "memory_delete"
    description = "Delete a memory by id."
    permissions = [Permission.memory_delete]
    InputModel = MemoryDeleteInput

    def execute(self, params: MemoryDeleteInput):
        ok = memory_service.delete(params.id)
        if not ok:
            raise RuntimeError(f"No memory with id {params.id}")
        return {"deleted": params.id}, f"deleted memory {params.id}"
