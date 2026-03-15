"""The NL-to-SQL agent.

This is a hand-rolled tool-calling loop rather than a pre-built agent executor.
The reason is deliberate: the loop here is short and the one action it can take
(running SQL) is security-critical, so explicit control over every round-trip —
what the model asked for, what we validated, what we ran, what came back — is
worth more than the convenience of a framework that hides those steps. (This
contrasts with the LangGraph multi-agent project, where a graph of cooperating
agents genuinely benefits from orchestration; see the README.)

The loop:

    1. Send the conversation + the run_sql tool to the model.
    2. If the model calls run_sql -> guard + execute + feed the result back.
    3. Repeat until the model answers in plain text, or we hit the step cap.

Every executed query is captured in a ``steps`` trace so the UI can show the
exact SQL, the rows, and the timing behind each answer — the audit trail.
"""
from __future__ import annotations

import time
from typing import Any, Protocol

from .config import get_settings
from .schema_inspector import get_schema
from .tools import TOOLS, execute_run_sql, tool_result_payload

_SYSTEM_TEMPLATE = """You are QueryPilot, a careful data analyst for a \
pharmaceutical manufacturing database. You answer questions by querying the \
database and explaining what the data shows.

You have one tool, run_sql, which runs a single read-only PostgreSQL SELECT and \
returns rows. Use it to get real numbers — never invent data, column names, or \
table names that are not in the schema below.

How to work:
- Read the question, then call run_sql with a single SELECT to get the answer.
- Use explicit JOINs based on the foreign keys shown in the schema.
- Filter text columns using the exact values listed under "values:" comments.
- You may call run_sql more than once to explore or refine, but be efficient.
- When you have the data, give a short, direct answer in plain English that \
states the actual figures. Mention the key numbers; don't just describe what \
you did. If results were truncated or a query failed, say so honestly.
- If the question cannot be answered from this schema, say what's missing \
rather than guessing.

Database schema (PostgreSQL):

{schema}
"""


class AnthropicClient(Protocol):
    """Minimal structural type for the Anthropic client we depend on.

    Declaring it as a Protocol lets tests inject a fake client without the
    real SDK or network access.
    """

    class messages:  # noqa: N801 - mirrors the SDK shape
        @staticmethod
        def create(**kwargs: Any) -> Any: ...


def _build_system_prompt() -> str:
    schema_prompt = get_schema()["schema_prompt"]
    return _SYSTEM_TEMPLATE.format(schema=schema_prompt)


def _content_to_dicts(content: list[Any]) -> list[dict[str, Any]]:
    """Convert SDK content blocks into plain dicts for storage and replay."""
    blocks: list[dict[str, Any]] = []
    for block in content:
        btype = getattr(block, "type", None)
        if btype == "text":
            blocks.append({"type": "text", "text": block.text})
        elif btype == "tool_use":
            blocks.append(
                {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                }
            )
    return blocks


def _final_text(content: list[Any]) -> str:
    parts = [b.text for b in content if getattr(b, "type", None) == "text"]
    return "\n".join(p for p in parts if p).strip()


def run_agent(
    client: AnthropicClient,
    user_message: str,
    history: list[dict[str, Any]],
) -> dict[str, Any]:
    """Run the agent for one user turn.

    Args:
        client: an Anthropic client (or compatible fake).
        user_message: the new natural-language question.
        history: prior messages for this session (may be empty).

    Returns a dict with:
        answer: the final plain-text answer.
        steps:  list of executed-query traces (sql, columns, rows, timing...).
        new_messages: the messages to append to the session (this user turn,
                      the assistant tool calls, the tool results, and the final
                      assistant answer), ready to persist.
    """
    settings = get_settings()
    system_prompt = _build_system_prompt()

    # Working copy: history + the new user message.
    messages: list[dict[str, Any]] = list(history)
    messages.append({"role": "user", "content": user_message})

    # Everything added this turn, to persist into memory at the end.
    new_messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
    steps: list[dict[str, Any]] = []

    for _ in range(settings.max_agent_steps):
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=settings.max_tokens,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        assistant_blocks = _content_to_dicts(response.content)
        assistant_msg = {"role": "assistant", "content": assistant_blocks}
        messages.append(assistant_msg)
        new_messages.append(assistant_msg)

        if getattr(response, "stop_reason", None) != "tool_use":
            answer = _final_text(response.content)
            return {"answer": answer, "steps": steps, "new_messages": new_messages}

        # Execute every tool call the model requested in this turn.
        tool_results: list[dict[str, Any]] = []
        for block in response.content:
            if getattr(block, "type", None) != "tool_use":
                continue
            if block.name != "run_sql":
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": '{"ok": false, "error": "Unknown tool."}',
                        "is_error": True,
                    }
                )
                continue

            started = time.perf_counter()
            result = execute_run_sql(block.input or {})
            elapsed_ms = round((time.perf_counter() - started) * 1000, 1)

            steps.append(
                {
                    "purpose": (block.input or {}).get("purpose"),
                    "sql": result.get("sql", (block.input or {}).get("query", "")),
                    "ok": result.get("ok", False),
                    "error": result.get("error"),
                    "columns": result.get("columns", []),
                    "rows": result.get("rows", []),
                    "row_count": result.get("row_count", 0),
                    "truncated": result.get("truncated", False),
                    "elapsed_ms": elapsed_ms,
                }
            )

            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": tool_result_payload(result),
                    "is_error": not result.get("ok", False),
                }
            )

        tool_msg = {"role": "user", "content": tool_results}
        messages.append(tool_msg)
        new_messages.append(tool_msg)

    # Step cap reached. Ask the model to answer with what it has, no more tools.
    final = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=settings.max_tokens,
        system=system_prompt,
        messages=messages
        + [
            {
                "role": "user",
                "content": (
                    "You've reached the query limit for this question. "
                    "Answer as best you can with the results so far."
                ),
            }
        ],
    )
    answer = _final_text(final.content) or (
        "I wasn't able to complete this within the query limit. "
        "Try narrowing the question."
    )
    fallback_assistant = {"role": "assistant", "content": _content_to_dicts(final.content)}
    new_messages.append(fallback_assistant)
    return {"answer": answer, "steps": steps, "new_messages": new_messages}
