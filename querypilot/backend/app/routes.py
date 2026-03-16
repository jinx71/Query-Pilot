"""API routes."""
from __future__ import annotations

import anthropic
from fastapi import APIRouter, HTTPException

from . import agent as agent_module
from .config import get_settings
from .memory import store
from .models import (
    ChatData,
    ChatRequest,
    Envelope,
    QueryStep,
    SchemaData,
    SessionData,
)
from .schema_inspector import get_schema

router = APIRouter()

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    """Lazily build the Anthropic client so the app can start (and serve
    /health and /schema) even before a key is configured."""
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise HTTPException(
                status_code=503,
                detail="ANTHROPIC_API_KEY is not configured on the server.",
            )
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


@router.get("/health", response_model=Envelope[dict])
def health() -> Envelope[dict]:
    return Envelope(success=True, data={"status": "ok"}, message="healthy")


@router.post("/api/session", response_model=Envelope[SessionData])
def create_session() -> Envelope[SessionData]:
    session_id = store.new_session()
    return Envelope(
        success=True,
        data=SessionData(session_id=session_id),
        message="session created",
    )


@router.post("/api/session/{session_id}/reset", response_model=Envelope[SessionData])
def reset_session(session_id: str) -> Envelope[SessionData]:
    if not store.exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    store.reset(session_id)
    return Envelope(
        success=True,
        data=SessionData(session_id=session_id),
        message="session reset",
    )


@router.get("/api/schema", response_model=Envelope[SchemaData])
def schema() -> Envelope[SchemaData]:
    """Return the database schema for the sidebar."""
    try:
        tree = get_schema()["schema_tree"]
    except Exception as exc:  # database unreachable
        raise HTTPException(
            status_code=503, detail=f"Could not read database schema: {exc}"
        )
    return Envelope(
        success=True, data=SchemaData(**tree), message="schema loaded"
    )


@router.post("/api/chat", response_model=Envelope[ChatData])
def chat(payload: ChatRequest) -> Envelope[ChatData]:
    """Answer a natural-language question against the database."""
    client = get_client()

    # Resolve or create the session.
    session_id = payload.session_id
    if not session_id or not store.exists(session_id):
        session_id = store.new_session()

    history = store.get_messages(session_id)

    try:
        result = agent_module.run_agent(
            client=client, user_message=payload.message, history=history
        )
    except anthropic.APIStatusError as exc:
        raise HTTPException(
            status_code=502, detail=f"Model API error: {exc.message}"
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}")

    store.append(session_id, result["new_messages"])

    steps = [QueryStep(**step) for step in result["steps"]]
    return Envelope(
        success=True,
        data=ChatData(
            session_id=session_id, answer=result["answer"], steps=steps
        ),
        message="ok",
    )
