"""Pydantic schemas for the memory engine."""
from __future__ import annotations

import time
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MemoryType(str, Enum):
    user_preference = "user_preference"
    project_fact = "project_fact"
    long_term_goal = "long_term_goal"
    repeated_instruction = "repeated_instruction"
    task_note = "task_note"
    personal_note = "personal_note"
    technical_context = "technical_context"
    writing_style_preference = "writing_style_preference"


class MemoryItem(BaseModel):
    id: str
    type: MemoryType = MemoryType.task_note
    content: str
    tags: list[str] = Field(default_factory=list)
    importance: float = 0.5
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    source: str = "user"
    user_confirmed: bool = False
    sensitive_flag: bool = False


class MemoryCreate(BaseModel):
    content: str
    type: MemoryType = MemoryType.task_note
    tags: list[str] = Field(default_factory=list)
    importance: float = 0.5
    source: str = "user"
    user_confirmed: bool = True
    sensitive_flag: bool = False


class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    type: Optional[MemoryType] = None
    tags: Optional[list[str]] = None
    importance: Optional[float] = None
    user_confirmed: Optional[bool] = None
    sensitive_flag: Optional[bool] = None


class MemorySearchResult(BaseModel):
    item: MemoryItem
    score: float
