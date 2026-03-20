"""Tests for the hand-rolled agent loop.

A scripted fake Anthropic client stands in for the real model, so the loop's
control flow is tested deterministically and without network access. The tool
the agent calls still runs for real against the seeded database, so these
exercise the full chain: loop -> tool -> guard -> DB -> result -> model.
"""
from types import SimpleNamespace

import pytest

from app.agent import run_agent

pytestmark = pytest.mark.requires_db


# --- fake SDK objects --------------------------------------------------------

def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_block(tool_id, query, purpose="find it"):
    return SimpleNamespace(
        type="tool_use",
        id=tool_id,
        name="run_sql",
        input={"query": query, "purpose": purpose},
    )


def response(content, stop_reason):
    return SimpleNamespace(content=content, stop_reason=stop_reason)


class FakeClient:
    """Replays a list of pre-scripted responses, one per messages.create call."""

    def __init__(self, scripted):
        self._scripted = list(scripted)
        self.calls = []
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kwargs):
        # Snapshot the messages list as the real SDK would serialise it at call
        # time; run_agent mutates its working list in place across the loop.
        snapshot = dict(kwargs)
        snapshot["messages"] = list(kwargs.get("messages", []))
        self.calls.append(snapshot)
        return self._scripted.pop(0)


# --- tests -------------------------------------------------------------------

def test_single_tool_call_then_answer():
    scripted = [
        response(
            [tool_block("t1", "SELECT count(*) AS n FROM batches")],
            stop_reason="tool_use",
        ),
        response([text_block("There are 320 batches.")], stop_reason="end_turn"),
    ]
    client = FakeClient(scripted)

    result = run_agent(client, "How many batches are there?", history=[])

    assert result["answer"] == "There are 320 batches."
    assert len(result["steps"]) == 1
    step = result["steps"][0]
    assert step["ok"] is True
    assert step["rows"][0]["n"] == 320
    assert step["elapsed_ms"] >= 0
    # The conversation to persist includes user, assistant(tool), tool_result, assistant(text).
    assert len(result["new_messages"]) == 4


def test_rejected_query_is_fed_back_and_agent_recovers():
    scripted = [
        # Model first tries a write -> guard rejects -> error returned to model.
        response(
            [tool_block("t1", "DELETE FROM batches")],
            stop_reason="tool_use",
        ),
        # Model recovers with a safe read.
        response(
            [tool_block("t2", "SELECT count(*) AS n FROM batches WHERE status = 'rejected'")],
            stop_reason="tool_use",
        ),
        response([text_block("Some batches were rejected.")], stop_reason="end_turn"),
    ]
    client = FakeClient(scripted)

    result = run_agent(client, "Delete everything", history=[])

    assert len(result["steps"]) == 2
    assert result["steps"][0]["ok"] is False  # the write was blocked
    assert "guard" in result["steps"][0]["error"].lower()
    assert result["steps"][1]["ok"] is True   # the recovery query ran
    assert result["answer"]


def test_history_is_preserved_for_followups():
    history = [
        {"role": "user", "content": "How many products?"},
        {"role": "assistant", "content": [{"type": "text", "text": "12 products."}]},
    ]
    scripted = [
        response(
            [tool_block("t1", "SELECT count(*) AS n FROM batches")],
            stop_reason="tool_use",
        ),
        response([text_block("320 batches.")], stop_reason="end_turn"),
    ]
    client = FakeClient(scripted)

    run_agent(client, "And how many batches?", history=history)

    # The first model call must include the prior turns plus the new question.
    first_call_messages = client.calls[0]["messages"]
    assert first_call_messages[0]["content"] == "How many products?"
    assert first_call_messages[-1]["content"] == "And how many batches?"


def test_step_cap_is_enforced(monkeypatch):
    from app import agent as agent_module

    settings = agent_module.get_settings()
    monkeypatch.setattr(settings, "max_agent_steps", 2)
    # Always ask for another tool call -> would loop forever without the cap.
    looping = [
        response([tool_block(f"t{i}", "SELECT 1 AS n")], stop_reason="tool_use")
        for i in range(5)
    ]
    # Final forced answer after the cap.
    looping.append(response([text_block("Stopping here.")], stop_reason="end_turn"))
    client = FakeClient(looping)

    result = run_agent(client, "loop forever", history=[])
    # Capped at 2 tool round-trips + 1 forced final call.
    assert len(result["steps"]) <= 3
    assert result["answer"]
