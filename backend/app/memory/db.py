"""SQLAlchemy engine + ORM models for local persistence.

A single local SQLite database stores long-term memory and indexed-file
metadata. The vector data itself lives in the RAG vector store.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from sqlalchemy import Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from ..config import get_settings


class Base(DeclarativeBase):
    pass


class MemoryRow(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    type: Mapped[str] = mapped_column(String(40), index=True)
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[str] = mapped_column(String(500), default="")  # comma-separated
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)
    updated_at: Mapped[float] = mapped_column(Float, default=time.time)
    source: Mapped[str] = mapped_column(String(120), default="user")
    user_confirmed: Mapped[int] = mapped_column(Integer, default=0)
    sensitive_flag: Mapped[int] = mapped_column(Integer, default=0)


class IndexedFileRow(Base):
    __tablename__ = "indexed_files"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    filename: Mapped[str] = mapped_column(String(500))
    path: Mapped[str] = mapped_column(String(1000), default="")
    file_type: Mapped[str] = mapped_column(String(20), default="")
    num_chunks: Mapped[int] = mapped_column(Integer, default=0)
    bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[float] = mapped_column(Float, default=time.time)


_engine = None
_Session = None


def init_engine(db_path: Optional[Path] = None):
    global _engine, _Session
    settings = get_settings()
    path = db_path or settings.db_path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(f"sqlite:///{path}", future=True)
    Base.metadata.create_all(_engine)
    _Session = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def get_session():
    if _Session is None:
        init_engine()
    return _Session()  # type: ignore[misc]
