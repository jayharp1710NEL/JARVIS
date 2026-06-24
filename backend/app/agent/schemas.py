"""Pydantic schemas shared across the agent, API and tools."""
from __future__ import annotations

import time
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Conversation
# ---------------------------------------------------------------------------
class Role(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class Message(BaseModel):
    role: Role
    content: str
    name: Optional[str] = None

    def to_provider(self) -> dict[str, str]:
        d = {"role": self.role.value, "content": self.content}
        if self.name:
            d["name"] = self.name
        return d


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------
class Mode(str, Enum):
    fast = "fast"
    research = "research"
    deep = "deep"
    builder = "builder"
    truth = "truth"
    debate = "debate"
    privacy = "privacy"
    autopilot = "autopilot"


# ---------------------------------------------------------------------------
# Task classification
# ---------------------------------------------------------------------------
class TaskType(str, Enum):
    casual = "casual"
    factual = "factual"
    current_info = "current_info"
    research = "research"
    coding = "coding"
    math = "math"
    document_qa = "document_qa"
    memory_qa = "memory_qa"
    planning = "planning"
    creative = "creative"
    high_risk = "high_risk"  # medical / legal / financial
    automation = "automation"


class Classification(BaseModel):
    task_type: TaskType
    needs_web: bool = False
    needs_files: bool = False
    needs_memory: bool = False
    needs_math: bool = False
    needs_url_read: bool = False
    is_high_risk: bool = False
    rationale: str = ""


class PlanStep(BaseModel):
    id: int
    description: str
    tool: Optional[str] = None
    done: bool = False


class Plan(BaseModel):
    steps: list[PlanStep] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Sources & citations
# ---------------------------------------------------------------------------
SourceType = Literal[
    "official", "academic", "documentation", "news", "blog",
    "forum", "commercial", "unknown",
]


class Source(BaseModel):
    id: str
    title: str
    url: str
    domain: str = ""
    snippet: str = ""
    full_text_excerpt: str = ""
    retrieved_at: float = Field(default_factory=time.time)
    published_at: Optional[str] = None
    provider: str = "unknown"
    credibility_score: float = 0.5
    source_type: SourceType = "unknown"
    citation_label: str = ""


class FileCitation(BaseModel):
    filename: str
    page: Optional[int] = None
    chunk_id: str
    excerpt: str
    score: float = 0.0


# ---------------------------------------------------------------------------
# Claims / verification
# ---------------------------------------------------------------------------
ClaimStatus = Literal["verified", "likely", "uncertain", "contradicted", "speculative"]


class Claim(BaseModel):
    text: str
    status: ClaimStatus = "uncertain"
    support: list[str] = Field(default_factory=list)  # source ids supporting
    contradict: list[str] = Field(default_factory=list)
    note: str = ""


# ---------------------------------------------------------------------------
# Tool tracing
# ---------------------------------------------------------------------------
class ToolCallTrace(BaseModel):
    tool: str
    input: dict[str, Any] = Field(default_factory=dict)
    ok: bool = True
    summary: str = ""
    error: Optional[str] = None
    duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# Confidence
# ---------------------------------------------------------------------------
class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


# ---------------------------------------------------------------------------
# Chat request / response
# ---------------------------------------------------------------------------
class ModelSettings(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None


class ChatRequest(BaseModel):
    message: str
    history: list[Message] = Field(default_factory=list)
    mode: Mode = Mode.fast
    settings: ModelSettings = Field(default_factory=ModelSettings)
    use_web: Optional[bool] = None        # None => let the router decide
    use_memory: Optional[bool] = None
    use_files: Optional[bool] = None
    local_privacy: bool = False
    file_ids: list[str] = Field(default_factory=list)
    session_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    mode: Mode
    sources: list[Source] = Field(default_factory=list)
    file_citations: list[FileCitation] = Field(default_factory=list)
    memory_used: list[str] = Field(default_factory=list)
    tool_trace: list[ToolCallTrace] = Field(default_factory=list)
    claims: list[Claim] = Field(default_factory=list)
    confidence: Confidence = Confidence.medium
    uncertainty: list[str] = Field(default_factory=list)
    reasoning_summary: str = ""
    next_best_action: str = ""
    warnings: list[str] = Field(default_factory=list)
