"""Tests for the SQL safety guard.

This is the project's security boundary, so it is tested the hardest: every
category of write, every injection trick (comment smuggling, statement
chaining, dangerous functions), and the legitimate read shapes the agent should
be allowed to run.
"""
import pytest

from app import sql_guard
from app.sql_guard import UnsafeQueryError


# --- queries that MUST be allowed -------------------------------------------

ALLOWED = [
    "SELECT * FROM batches",
    "select count(*) from qc_tests where result = 'fail'",
    "SELECT p.name, COUNT(*) FROM batches b JOIN products p ON b.product_id = p.id GROUP BY p.name",
    "SELECT * FROM batches ORDER BY manufactured_date DESC LIMIT 10",
    # CTE that resolves to a SELECT is read-only and allowed.
    "WITH recent AS (SELECT * FROM batches WHERE manufactured_date > '2024-01-01') SELECT count(*) FROM recent",
    # Subquery.
    "SELECT name FROM products WHERE id IN (SELECT product_id FROM batches WHERE status = 'rejected')",
    # Comment alongside a legitimate query is fine (comments are stripped).
    "SELECT 1 -- a harmless comment",
]


@pytest.mark.parametrize("sql", ALLOWED)
def test_allows_read_only_selects(sql):
    cleaned = sql_guard.validate(sql)
    assert cleaned  # returns non-empty cleaned SQL
    assert not cleaned.endswith(";")


# --- write statements that MUST be rejected ---------------------------------

WRITES = [
    "DELETE FROM batches",
    "DELETE FROM batches WHERE id = 1",
    "UPDATE batches SET status = 'released'",
    "INSERT INTO batches (batch_number) VALUES ('x')",
    "DROP TABLE batches",
    "DROP DATABASE querypilot",
    "TRUNCATE qc_tests",
    "ALTER TABLE batches ADD COLUMN hacked TEXT",
    "CREATE TABLE evil (id INT)",
    "GRANT ALL ON batches TO public",
    "REVOKE SELECT ON batches FROM querypilot",
    "MERGE INTO batches USING products ON true WHEN MATCHED THEN DELETE",
]


@pytest.mark.parametrize("sql", WRITES)
def test_rejects_writes(sql):
    with pytest.raises(UnsafeQueryError):
        sql_guard.validate(sql)


# --- injection / evasion attempts that MUST be rejected ---------------------

INJECTIONS = [
    # Statement chaining: piggyback a write onto a read.
    "SELECT 1; DROP TABLE batches",
    "SELECT * FROM batches; DELETE FROM batches",
    "SELECT 1;;DROP TABLE batches",
    # Comment-smuggled write: the leading keyword check must look past comments.
    "/* hello */ DROP TABLE batches",
    "-- comment\nDELETE FROM batches",
    # Write hidden inside a CTE.
    "WITH x AS (DELETE FROM batches RETURNING *) SELECT * FROM x",
    # Transaction / session control.
    "BEGIN; DELETE FROM batches; COMMIT",
    "SET ROLE postgres",
    # Dangerous server-side functions.
    "SELECT pg_read_file('/etc/passwd')",
    "SELECT pg_sleep(60)",
    "SELECT lo_export(1, '/tmp/x')",
    # COPY to/from filesystem.
    "COPY batches TO '/tmp/dump.csv'",
]


@pytest.mark.parametrize("sql", INJECTIONS)
def test_rejects_injection_attempts(sql):
    with pytest.raises(UnsafeQueryError):
        sql_guard.validate(sql)


# --- edge cases --------------------------------------------------------------

def test_rejects_empty():
    with pytest.raises(UnsafeQueryError):
        sql_guard.validate("")
    with pytest.raises(UnsafeQueryError):
        sql_guard.validate("   ")


def test_rejects_comment_only():
    with pytest.raises(UnsafeQueryError):
        sql_guard.validate("-- just a comment")


def test_trailing_semicolon_is_stripped():
    assert sql_guard.validate("SELECT 1;") == "SELECT 1"


def test_non_select_leader_rejected():
    with pytest.raises(UnsafeQueryError):
        sql_guard.validate("EXPLAIN SELECT * FROM batches")


# --- row limit injection -----------------------------------------------------

def test_apply_row_limit_appends_when_absent():
    out = sql_guard.apply_row_limit("SELECT * FROM batches", 200)
    assert out.strip().endswith("LIMIT 200")


def test_apply_row_limit_respects_existing_limit():
    sql = "SELECT * FROM batches LIMIT 5"
    assert sql_guard.apply_row_limit(sql, 200) == sql


def test_apply_row_limit_coerces_int():
    out = sql_guard.apply_row_limit("SELECT 1", 50)
    assert "LIMIT 50" in out
