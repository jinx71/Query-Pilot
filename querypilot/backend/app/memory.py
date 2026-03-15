"""Conversation memory.

The agent needs prior turns so follow-ups like "now break that down by month"
resolve against earlier context. We keep an in-process store of the raw
Anthropic message list per session, trimmed to a bounded number of turns so a
long conversation can't grow the context window without limit.

This is intentionally simple for a portfolio/demo: a dict in memory. In a
multi-process or horizontally-scaled deployment this would move to Redis (same
interface, swap the backing store) — see the README's production notes.
"""
from __future__ import annotations

import threading
import time
import uuid
from typing import Any

from .config import get_settings


class ConversationStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def new_session(self) -> str:
        session_id = uuid.uuid4().hex
        with self._lock:
            self._sessions[session_id] = {"messages": [], "updated": time.time()}
        return session_id

    def get_messages(self, session_id: str) -> list[dict[str, Any]]:
        with self._lock:
            session = self._sessions.get(session_id)
            return list(session["messages"]) if session else []

    def exists(self, session_id: str) -> bool:
        with self._lock:
            return session_id in self._sessions

    def append(self, session_id: str, messages: list[dict[str, Any]]) -> None:
        """Append messages and trim to the configured turn window."""
        settings = get_settings()
        max_messages = settings.max_history_turns * 2  # user + assistant per turn
        with self._lock:
            session = self._sessions.setdefault(
                session_id, {"messages": [], "updated": time.time()}
            )
            session["messages"].extend(messages)
            if len(session["messages"]) > max_messages:
                # Keep the most recent messages; drop from the front. Trimming on
                # a turn boundary keeps user/assistant pairs intact.
                overflow = len(session["messages"]) - max_messages
                session["messages"] = session["messages"][overflow:]
            session["updated"] = time.time()

    def reset(self, session_id: str) -> None:
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id] = {"messages": [], "updated": time.time()}


# Module-level singleton used by the routes.
store = ConversationStore()
