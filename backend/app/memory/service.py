"""Memory service — CRUD + keyword relevance search over local SQLite.

Search is deliberately dependency-free (keyword + tag + importance scoring)
so memory works without any embedding model. The agent uses this to recall
user preferences, project facts, goals and notes.
"""
from __future__ import annotations

import re
import uuid
from typing import Optional

from .db import MemoryRow, get_session
from .schemas import (
    MemoryCreate,
    MemoryItem,
    MemorySearchResult,
    MemoryType,
    MemoryUpdate,
)

_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def _row_to_item(row: MemoryRow) -> MemoryItem:
    return MemoryItem(
        id=row.id,
        type=MemoryType(row.type),
        content=row.content,
        tags=[t for t in row.tags.split(",") if t],
        importance=row.importance,
        created_at=row.created_at,
        updated_at=row.updated_at,
        source=row.source,
        user_confirmed=bool(row.user_confirmed),
        sensitive_flag=bool(row.sensitive_flag),
    )


class MemoryService:
    def save(self, data: MemoryCreate) -> MemoryItem:
        item = MemoryItem(
            id=uuid.uuid4().hex[:12],
            type=data.type,
            content=data.content.strip(),
            tags=[t.strip() for t in data.tags if t.strip()],
            importance=max(0.0, min(1.0, data.importance)),
            source=data.source,
            user_confirmed=data.user_confirmed,
            sensitive_flag=data.sensitive_flag,
        )
        with get_session() as s:
            s.add(
                MemoryRow(
                    id=item.id,
                    type=item.type.value,
                    content=item.content,
                    tags=",".join(item.tags),
                    importance=item.importance,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    source=item.source,
                    user_confirmed=int(item.user_confirmed),
                    sensitive_flag=int(item.sensitive_flag),
                )
            )
            s.commit()
        return item

    def get(self, mem_id: str) -> Optional[MemoryItem]:
        with get_session() as s:
            row = s.get(MemoryRow, mem_id)
            return _row_to_item(row) if row else None

    def list(self, limit: int = 200, type: Optional[MemoryType] = None) -> list[MemoryItem]:
        with get_session() as s:
            q = s.query(MemoryRow)
            if type:
                q = q.filter(MemoryRow.type == type.value)
            rows = (
                q.order_by(MemoryRow.importance.desc(), MemoryRow.updated_at.desc())
                .limit(limit)
                .all()
            )
            return [_row_to_item(r) for r in rows]

    def search(self, query: str, top_k: int = 5) -> list[MemorySearchResult]:
        q_tokens = _tokens(query)
        results: list[MemorySearchResult] = []
        with get_session() as s:
            rows = s.query(MemoryRow).all()
        for row in rows:
            item = _row_to_item(row)
            content_tokens = _tokens(item.content)
            tag_tokens = _tokens(" ".join(item.tags))
            overlap = len(q_tokens & content_tokens)
            tag_overlap = len(q_tokens & tag_tokens)
            if overlap == 0 and tag_overlap == 0:
                # Allow substring match for short queries
                if query.strip().lower() not in item.content.lower():
                    continue
            score = (
                overlap * 1.0
                + tag_overlap * 1.5
                + item.importance * 0.5
                + (0.3 if item.user_confirmed else 0.0)
            )
            results.append(MemorySearchResult(item=item, score=round(score, 3)))
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:top_k]

    def update(self, mem_id: str, data: MemoryUpdate) -> Optional[MemoryItem]:
        import time

        with get_session() as s:
            row = s.get(MemoryRow, mem_id)
            if not row:
                return None
            if data.content is not None:
                row.content = data.content
            if data.type is not None:
                row.type = data.type.value
            if data.tags is not None:
                row.tags = ",".join(data.tags)
            if data.importance is not None:
                row.importance = max(0.0, min(1.0, data.importance))
            if data.user_confirmed is not None:
                row.user_confirmed = int(data.user_confirmed)
            if data.sensitive_flag is not None:
                row.sensitive_flag = int(data.sensitive_flag)
            row.updated_at = time.time()
            s.commit()
            return _row_to_item(row)

    def delete(self, mem_id: str) -> bool:
        with get_session() as s:
            row = s.get(MemoryRow, mem_id)
            if not row:
                return False
            s.delete(row)
            s.commit()
            return True

    def wipe_all(self) -> int:
        with get_session() as s:
            n = s.query(MemoryRow).delete()
            s.commit()
            return n


memory_service = MemoryService()
