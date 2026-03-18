"""Apply schema.sql and seed_data.sql to the configured database.

For local setups that aren't using Docker (Docker auto-seeds via the init
scripts). Reads DATABASE_URL the same way the app does.

    python -m seed.run        # from the backend/ directory
"""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text

from app.config import get_settings

HERE = Path(__file__).parent


def _run_sql_file(engine, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.exec_driver_sql(sql)
    print(f"applied {path.name}")


def main() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url)
    _run_sql_file(engine, HERE / "schema.sql")
    _run_sql_file(engine, HERE / "seed_data.sql")

    with engine.connect() as conn:
        n = conn.execute(text("SELECT count(*) FROM batches")).scalar()
    print(f"done — {n} batches loaded")


if __name__ == "__main__":
    main()
