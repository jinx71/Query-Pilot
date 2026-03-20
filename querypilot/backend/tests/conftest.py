"""Shared pytest fixtures.

DB-backed tests are marked ``requires_db`` and skip automatically when no
database can be reached, so the pure-logic tests (the SQL guard) always run
anywhere — including a fresh checkout with no Postgres — while the integration
tests run in CI against a real Postgres service container.
"""
from __future__ import annotations

import os

import pytest


def _db_available() -> bool:
    try:
        from sqlalchemy import text

        from app.database import get_engine

        with get_engine().connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return True
    except Exception:
        return False


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "requires_db: test needs a reachable PostgreSQL database"
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if _db_available():
        return
    skip = pytest.mark.skip(reason="no database reachable (DATABASE_URL)")
    for item in items:
        if "requires_db" in item.keywords:
            item.add_marker(skip)


@pytest.fixture(scope="session")
def anthropic_key_set() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))
