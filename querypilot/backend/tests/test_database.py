"""Integration tests for the read-only database layer.

These run against a real PostgreSQL instance (marked ``requires_db``) because
the protections being tested — read-only transactions, statement timeouts —
are database behaviours that a mock cannot exercise.
"""
import pytest
from sqlalchemy.exc import DBAPIError, InternalError, OperationalError

from app.database import run_readonly_query

pytestmark = pytest.mark.requires_db


def test_simple_select_returns_rows():
    result = run_readonly_query("SELECT id, name FROM products ORDER BY id LIMIT 3")
    assert result["columns"] == ["id", "name"]
    assert result["row_count"] == 3
    assert result["rows"][0]["name"]  # values present
    assert result["truncated"] is False


def test_aggregate_query():
    result = run_readonly_query("SELECT count(*) AS n FROM batches")
    assert result["rows"][0]["n"] == 320


def test_row_cap_and_truncation_flag():
    # 320 batches exist; cap at 10 and expect truncation to be reported.
    result = run_readonly_query("SELECT id FROM batches", max_rows=10)
    assert result["row_count"] == 10
    assert result["truncated"] is True


def test_decimal_and_date_are_jsonable():
    result = run_readonly_query(
        "SELECT measured_value, tested_date FROM qc_tests "
        "WHERE measured_value IS NOT NULL LIMIT 1"
    )
    row = result["rows"][0]
    assert isinstance(row["measured_value"], (int, float))
    assert isinstance(row["tested_date"], str)  # ISO string, not a date object


def test_write_is_rejected_at_db_level():
    # Even bypassing the SQL guard, the read-only transaction must refuse writes.
    with pytest.raises((DBAPIError, InternalError, OperationalError)):
        run_readonly_query("UPDATE batches SET status = 'released' WHERE id = 1")


def test_statement_timeout_cancels_long_query():
    with pytest.raises((DBAPIError, OperationalError)):
        # pg_sleep would run far longer than the 50ms cap we set here.
        run_readonly_query("SELECT pg_sleep(5)", timeout_ms=50)
