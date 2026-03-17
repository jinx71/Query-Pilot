"""SQL safety guard.

An NL-to-SQL agent generates SQL from untrusted natural language and runs it.
That is only safe if every generated statement is provably read-only and
single. This module is the application-level gate that enforces that *before*
any SQL reaches the database. It is one of three layers of defence:

    1. This validator (reject anything that isn't a single SELECT/WITH).
    2. A read-only database transaction (Postgres rejects writes itself).
    3. A statement timeout + row cap (bound cost and blast radius).

Why a dedicated module: the guard is the security boundary of the whole app,
so it lives on its own, is pure (no DB, no network), and is the most heavily
tested file in the project.
"""
from __future__ import annotations

import re

import sqlparse
from sqlparse.sql import Statement
from sqlparse.tokens import DDL, DML, Keyword


class UnsafeQueryError(Exception):
    """Raised when a generated query fails a safety check."""


# Statements that read data. Anything whose leading keyword is not in this set
# is rejected outright.
_ALLOWED_LEADERS = {"SELECT", "WITH"}

# Keywords that must never appear anywhere in a query. Even inside a CTE or a
# subquery these indicate a write, a schema change, or privilege manipulation.
_FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "MERGE", "UPSERT",
    "DROP", "CREATE", "ALTER", "TRUNCATE", "RENAME",
    "GRANT", "REVOKE",
    "VACUUM", "ANALYZE", "REINDEX", "CLUSTER",
    "COPY", "CALL", "EXECUTE", "DO",
    "COMMIT", "ROLLBACK", "SAVEPOINT", "BEGIN", "SET", "RESET",
    "LOCK", "LISTEN", "NOTIFY", "DISCARD", "PREPARE", "DEALLOCATE",
}

# Functions Postgres exposes that can write to disk or run code. Blocked even
# though they appear in read position.
_FORBIDDEN_FUNCTIONS = re.compile(
    r"\b(pg_read_file|pg_ls_dir|pg_sleep|lo_import|lo_export|dblink|"
    r"pg_terminate_backend|pg_cancel_backend|copy_to|copy_from)\s*\(",
    re.IGNORECASE,
)


def _strip_comments(sql: str) -> str:
    """Remove SQL comments so they can't be used to smuggle keywords past the
    leading-keyword check (e.g. ``/*x*/ DROP``)."""
    return sqlparse.format(sql, strip_comments=True).strip()


def _split_statements(sql: str) -> list[Statement]:
    """Return non-empty parsed statements. More than one means a chained
    injection attempt such as ``SELECT 1; DROP TABLE batches``."""
    parsed = sqlparse.parse(sql)
    return [s for s in parsed if s.token_first(skip_cm=True) is not None]


def _leading_keyword(statement: Statement) -> str:
    token = statement.token_first(skip_cm=True)
    return token.value.upper() if token is not None else ""


def _iter_keywords(statement: Statement):
    """Yield uppercased keyword tokens (recursively) from a parsed statement."""
    for token in statement.flatten():
        if token.ttype in (Keyword, DML, DDL) or (
            token.ttype is not None and token.ttype in Keyword
        ):
            yield token.value.upper()


def validate(sql: str) -> str:
    """Validate and normalise a generated SQL string.

    Returns the cleaned (comment-stripped, trimmed) SQL ready for execution.
    Raises :class:`UnsafeQueryError` if any safety check fails.
    """
    if not sql or not sql.strip():
        raise UnsafeQueryError("Empty query.")

    cleaned = _strip_comments(sql)
    if not cleaned:
        raise UnsafeQueryError("Query contained only comments.")

    statements = _split_statements(cleaned)
    if len(statements) == 0:
        raise UnsafeQueryError("No executable statement found.")
    if len(statements) > 1:
        raise UnsafeQueryError(
            "Multiple statements are not allowed; submit a single SELECT."
        )

    statement = statements[0]

    leader = _leading_keyword(statement)
    if leader not in _ALLOWED_LEADERS:
        raise UnsafeQueryError(
            f"Only read-only SELECT queries are allowed (got '{leader or 'unknown'}')."
        )

    found_keywords = set(_iter_keywords(statement))
    forbidden_hit = found_keywords & _FORBIDDEN_KEYWORDS
    if forbidden_hit:
        offending = ", ".join(sorted(forbidden_hit))
        raise UnsafeQueryError(f"Disallowed keyword(s): {offending}.")

    if _FORBIDDEN_FUNCTIONS.search(cleaned):
        raise UnsafeQueryError("Disallowed function call in query.")

    # A WITH (CTE) is only allowed if its body ultimately drives a SELECT and
    # contains no data-modifying CTE (e.g. WITH ... AS (DELETE ...)). The
    # forbidden-keyword scan above already catches DELETE/UPDATE/INSERT inside
    # the CTE, so reaching here means the WITH is read-only.

    return cleaned.rstrip(";").strip()


def apply_row_limit(sql: str, max_rows: int) -> str:
    """Append a LIMIT to bound result size when the model didn't supply one.

    Detection is intentionally conservative: if a top-level LIMIT is already
    present we leave the query alone (it may be smaller than our cap), otherwise
    we wrap nothing and simply append a LIMIT. Wrapping in a subquery would
    break queries that already aggregate, so we append instead.
    """
    has_limit = re.search(r"\blimit\b\s+\d+\s*$", sql, re.IGNORECASE)
    if has_limit:
        return sql
    return f"{sql}\nLIMIT {int(max_rows)}"
