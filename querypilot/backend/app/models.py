"""API request and response models."""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Envelope(BaseModel, Generic[T]):
    """Consistent response wrapper used across the API."""

    success: bool
    data: T | None = None
    message: str = ""


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None


class QueryStep(BaseModel):
    purpose: str | None = None
    sql: str
    ok: bool
    error: str | None = None
    columns: list[str] = []
    rows: list[dict[str, Any]] = []
    row_count: int = 0
    truncated: bool = False
    elapsed_ms: float = 0.0


class ChatData(BaseModel):
    session_id: str
    answer: str
    steps: list[QueryStep] = []


class SessionData(BaseModel):
    session_id: str


class ColumnInfo(BaseModel):
    name: str
    type: str
    primary_key: bool = False
    nullable: bool = True
    references: str | None = None
    sample_values: list[str] | None = None


class TableInfo(BaseModel):
    name: str
    columns: list[ColumnInfo]


class SchemaData(BaseModel):
    tables: list[TableInfo]
