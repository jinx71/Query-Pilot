"""Application configuration.

All runtime configuration is loaded from environment variables (or a local
.env file in development). Nothing here is secret by default — secrets live in
the environment, never in source.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Anthropic ---
    anthropic_api_key: str = ""
    # Sonnet is the default: strong enough for reliable SQL generation without
    # paying Opus prices on every turn. Swap via env for cheaper/cheaper runs.
    anthropic_model: str = "claude-sonnet-4-6"
    max_tokens: int = 1024

    # --- Database (the agent connects with a read-only-intent URL) ---
    database_url: str = (
        "postgresql+psycopg://querypilot:querypilot@localhost:5432/querypilot"
    )

    # --- Query safety limits ---
    # Hard ceiling on rows returned to the model and the UI. Keeps token cost
    # and payload size bounded regardless of what the generated query asks for.
    max_result_rows: int = 200
    # Per-statement timeout enforced at the database level (milliseconds).
    statement_timeout_ms: int = 5000

    # --- Agent loop ---
    # Safety valve: the maximum number of tool round-trips before we stop and
    # ask the model to answer with what it has. Prevents runaway loops.
    max_agent_steps: int = 6
    # How many prior turns of a conversation to keep in working memory.
    max_history_turns: int = 12

    # --- CORS ---
    client_url: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
