"""Agent tools.

The agent is given exactly one tool: ``run_sql``. Keeping the toolset minimal
is deliberate — every additional tool is more surface area to secure and more
ways for the model to go off-script. ``run_sql`` is the only action the agent
can take in the world, and it is fully guarded.

Each tool call returns a structured result that goes back to the model as a
``tool_result`` block, and is also captured in the response trace so the UI can
render the exact query and rows the agent saw.
"""
from __future__ import annotations

import json
from typing import Any

from . import sql_guard
from .config import get_settings
from .database import run_readonly_query

# Anthropic tool schema. The description teaches the model the contract:
# read-only, single statement, Postgres dialect.
RUN_SQL_TOOL: dict[str, Any] = {
    "name": "run_sql",
    "description": (
        "Run a single read-only SQL SELECT query against the PostgreSQL "
        "database and return the resulting rows. Use this to answer the user's "
        "question with real data. Rules: exactly one statement; SELECT or WITH "
        "only; never INSERT/UPDATE/DELETE/DROP/ALTER or any write. Use standard "
        "PostgreSQL syntax. Prefer explicit JOINs using the foreign keys in the "
        "schema. If you need to look at the data before answering, call this "
        "tool; you may call it more than once to refine your query."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A single PostgreSQL SELECT statement.",
            },
            "purpose": {
                "type": "string",
                "description": "One short sentence: what this query is meant to find.",
            },
        },
        "required": ["query"],
    },
}

TOOLS: list[dict[str, Any]] = [RUN_SQL_TOOL]


def execute_run_sql(tool_input: dict[str, Any]) -> dict[str, Any]:
    """Execute the run_sql tool.

    Returns a dict with either result data or an ``error`` key. Errors are
    returned (not raised) so they can be handed back to the model as a
    tool_result — letting the agent see *why* a query was rejected and try a
    safe alternative, which is how a real analyst would recover.
    """
    settings = get_settings()
    raw_query = (tool_input or {}).get("query", "")

    try:
        safe_sql = sql_guard.validate(raw_query)
    except sql_guard.UnsafeQueryError as exc:
        return {"ok": False, "error": f"Query rejected by safety guard: {exc}"}

    limited_sql = sql_guard.apply_row_limit(safe_sql, settings.max_result_rows)

    try:
        result = run_readonly_query(limited_sql)
    except Exception as exc:  # surface DB errors back to the model to self-correct
        message = str(getattr(exc, "orig", exc)).strip().splitlines()[0]
        return {"ok": False, "error": f"Database error: {message}", "sql": limited_sql}

    return {
        "ok": True,
        "sql": limited_sql,
        "columns": result["columns"],
        "rows": result["rows"],
        "row_count": result["row_count"],
        "truncated": result["truncated"],
    }


def tool_result_payload(result: dict[str, Any]) -> str:
    """Serialise a tool result for the model.

    We cap how much row data goes back into the context window — the model
    needs to *see* the shape of the answer, not re-ingest hundreds of rows it
    already triggered. The full result still reaches the UI via the trace.
    """
    if not result.get("ok"):
        return json.dumps({"ok": False, "error": result.get("error")})

    rows = result["rows"]
    preview = rows[:50]
    payload = {
        "ok": True,
        "columns": result["columns"],
        "row_count": result["row_count"],
        "truncated": result["truncated"],
        "rows": preview,
    }
    if len(rows) > len(preview):
        payload["note"] = (
            f"Showing first {len(preview)} of {result['row_count']} rows."
        )
    return json.dumps(payload, default=str)
