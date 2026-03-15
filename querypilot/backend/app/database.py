"""Database access layer.

Exposes a single function, :func:`run_readonly_query`, which executes a
SELECT under three database-level protections:

    * ``default_transaction_read_only = on`` — Postgres rejects any write,
      so even if a write slipped past the SQL guard the database refuses it.
    * ``statement_timeout`` — a runaway or accidentally expensive query is
      cancelled rather than hanging the app.
    * ``fetchmany(max_rows)`` — we never pull an unbounded result set into
      memory or into the model's context.

Values returned from Postgres (Decimal, date, datetime, UUID) are normalised
to JSON-serialisable Python types so the same rows can go straight to the API.
"""
from __future__ import annotations

import datetime as dt
import decimal
import uuid
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import get_settings

_engine: Engine | None = None


def get_engine() -> Engine:
    """Lazily create and cache the SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,  # transparently recycle dead pooled connections
            pool_size=5,
            max_overflow=5,
        )
    return _engine


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, decimal.Decimal):
        # Keep integers as int, otherwise float — avoids "12.00" surprises.
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (dt.datetime, dt.date, dt.time)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).hex()
    return value


def run_readonly_query(
    sql: str, max_rows: int | None = None, timeout_ms: int | None = None
) -> dict[str, Any]:
    """Execute a read-only query and return columns + rows.

    Returns ``{"columns": [...], "rows": [{...}], "row_count": int,
    "truncated": bool}``. ``truncated`` is True when more rows existed than the
    cap allowed, so the UI and the model both know the answer is partial.
    """
    settings = get_settings()
    max_rows = max_rows or settings.max_result_rows
    timeout_ms = timeout_ms or settings.statement_timeout_ms

    engine = get_engine()
    with engine.connect() as conn:
        # AUTOCOMMIT lets these session settings take effect immediately and
        # persist for the duration of this connection's checkout.
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.exec_driver_sql(f"SET statement_timeout = {int(timeout_ms)}")
        conn.exec_driver_sql("SET default_transaction_read_only = on")

        result = conn.execute(text(sql))
        columns = list(result.keys())
        # Fetch one extra row to detect truncation without a second query.
        fetched = result.fetchmany(max_rows + 1)

    truncated = len(fetched) > max_rows
    rows_raw = fetched[:max_rows]
    rows = [
        {col: _to_jsonable(val) for col, val in zip(columns, row)} for row in rows_raw
    ]

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "truncated": truncated,
    }
