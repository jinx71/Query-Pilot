"""Schema introspection.

The model can only write correct SQL if it knows the tables, columns, and how
they join. We introspect the live database (rather than hardcoding a schema)
so the agent works against whatever database it's pointed at.

Two outputs are produced from one introspection pass:

    * ``schema_prompt`` — a compact text block embedded in the system prompt.
      It includes foreign keys (so the model joins correctly) and, for short
      low-cardinality text columns, the actual distinct values (so the model
      filters on ``'rejected'`` rather than guessing ``'failed'``).
    * ``schema_tree`` — structured JSON the frontend renders as a sidebar.

The result is cached: schema rarely changes within a session, and re-running
introspection on every request would be wasteful.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from sqlalchemy import inspect, text

from .database import get_engine

# Only surface distinct values for columns at or below this cardinality. These
# are the status/severity/category columns whose exact spelling the model needs.
_ENUM_SAMPLE_MAX_DISTINCT = 12
_ENUM_SAMPLE_TYPES = {"VARCHAR", "TEXT", "CHAR", "CHARACTER VARYING", "BPCHAR"}


def _distinct_values(table: str, column: str) -> list[str] | None:
    """Return distinct values for a column if it's low-cardinality, else None."""
    engine = get_engine()
    query = text(
        f'SELECT DISTINCT "{column}" AS v '
        f'FROM "{table}" WHERE "{column}" IS NOT NULL '
        f"LIMIT {_ENUM_SAMPLE_MAX_DISTINCT + 1}"
    )
    try:
        with engine.connect() as conn:
            conn = conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.exec_driver_sql("SET default_transaction_read_only = on")
            rows = conn.execute(query).fetchall()
    except Exception:
        return None
    if len(rows) > _ENUM_SAMPLE_MAX_DISTINCT:
        return None
    return [str(r[0]) for r in rows]


def _introspect() -> dict[str, Any]:
    engine = get_engine()
    inspector = inspect(engine)
    tables: list[dict[str, Any]] = []

    for table_name in sorted(inspector.get_table_names(schema="public")):
        pk = set(inspector.get_pk_constraint(table_name).get("constrained_columns") or [])
        fks = inspector.get_foreign_keys(table_name)
        fk_map = {
            col: (fk["referred_table"], fk["referred_columns"][i])
            for fk in fks
            for i, col in enumerate(fk["constrained_columns"])
        }

        columns: list[dict[str, Any]] = []
        for col in inspector.get_columns(table_name):
            col_type = str(col["type"]).upper()
            entry: dict[str, Any] = {
                "name": col["name"],
                "type": col_type,
                "primary_key": col["name"] in pk,
                "nullable": col.get("nullable", True),
            }
            if col["name"] in fk_map:
                ref_table, ref_col = fk_map[col["name"]]
                entry["references"] = f"{ref_table}.{ref_col}"

            base_type = col_type.split("(")[0].strip()
            if base_type in _ENUM_SAMPLE_TYPES:
                values = _distinct_values(table_name, col["name"])
                if values:
                    entry["sample_values"] = values
            columns.append(entry)

        tables.append({"name": table_name, "columns": columns})

    return {"tables": tables}


def _format_prompt(schema: dict[str, Any]) -> str:
    lines: list[str] = []
    for table in schema["tables"]:
        lines.append(f"TABLE {table['name']} (")
        for col in table["columns"]:
            parts = [f"  {col['name']} {col['type']}"]
            if col["primary_key"]:
                parts.append("PRIMARY KEY")
            if not col["nullable"]:
                parts.append("NOT NULL")
            if "references" in col:
                parts.append(f"REFERENCES {col['references']}")
            line = " ".join(parts)
            if "sample_values" in col:
                vals = ", ".join(repr(v) for v in col["sample_values"])
                line += f"   -- values: {vals}"
            lines.append(line)
        lines.append(")")
        lines.append("")
    return "\n".join(lines).strip()


@lru_cache
def get_schema() -> dict[str, Any]:
    """Return ``{"schema_tree": {...}, "schema_prompt": "..."}`` (cached)."""
    schema = _introspect()
    return {"schema_tree": schema, "schema_prompt": _format_prompt(schema)}


def clear_schema_cache() -> None:
    """Drop the cached schema (call after a migration in long-running processes)."""
    get_schema.cache_clear()
