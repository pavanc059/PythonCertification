"""
Assistant bot API.

POST /assistant/chat    — SSE streaming chat (contextual LLM answer)
GET  /assistant/history — past Q&A messages for the current user
DELETE /assistant/history — clear chat history
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.models import User
from dependencies import get_current_user, get_db
from assistant.context import build_user_context, ASSISTANT_SYSTEM_PROMPT
from assistant.models import AssistantMessageDB

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_HISTORY_MESSAGES = 10


def _build_fallback_response(context_block: str, question: str) -> list[str]:
    """
    Build a structured plain-text answer from the context block when the LLM
    is unreachable (network/firewall issue). Parses the sections we assembled
    and returns readable bullet-point summaries of each section.
    """
    lines = context_block.split("\n")
    sections: dict[str, list[str]] = {}
    current = ""
    for line in lines:
        if line.startswith("--- ") and line.endswith(" ---"):
            current = line.replace("---", "").strip()
            sections[current] = []
        elif current and line.strip() and not line.startswith("==="):
            sections[current].append(line.strip())

    parts = [
        "⚠️ *AI is currently unreachable from this network — showing your raw data instead.*\n",
        f"**Your question:** {question}\n",
    ]
    for section, items in sections.items():
        if items:
            parts.append(f"\n**{section}**")
            for item in items[:6]:  # cap each section
                parts.append(f"• {item}")

    parts.append(
        "\n\n*To enable AI-powered answers, ensure the backend container can reach "
        "api.openai.com or api.groq.com (check firewall/VPN settings).*"
    )
    return parts  # context window: last N turns


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
async def chat(
    body: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream an LLM response grounded in the user's live app data.

    The user's question + structured context (portfolio, bots, trades,
    activity log) are injected into the system prompt. The LLM can only
    describe facts that are actually in the DB — no hallucination on
    "why did X happen" questions.

    Returns: text/event-stream (SSE) — each chunk is `data: <text>\\n\\n`
    """
    question = body.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Build rich context from user's data
    context_block = build_user_context(current_user.id, question, db)

    # Persist the user turn
    db.add(AssistantMessageDB(
        user_id=current_user.id,
        role="user",
        content=question,
    ))
    db.commit()

    # Build conversation history (last N turns for multi-turn coherence)
    from sqlalchemy import desc
    history = (
        db.query(AssistantMessageDB)
        .filter_by(user_id=current_user.id)
        .order_by(desc(AssistantMessageDB.created_at))
        .limit(MAX_HISTORY_MESSAGES * 2)
        .all()
    )
    history = list(reversed(history))  # chronological order

    messages = [
        {"role": "system", "content": ASSISTANT_SYSTEM_PROMPT + "\n\n" + context_block},
    ]
    for msg in history[:-1]:  # exclude the just-added turn (already in context)
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": question})

    async def _stream():
        from config import settings
        from openai import AsyncOpenAI

        # ── Try LLM first ─────────────────────────────────────────────────
        llm_available = bool(settings.groq_api_key or settings.openai_api_key)

        if not llm_available:
            # No key — return structured context as a readable response
            for line in context_block.split("\n"):
                if line.strip():
                    yield f"data: {line.replace(chr(10), '<br>')}\n\n"
            yield "data: [DONE]\n\n"
            return

        if settings.groq_api_key:
            client = AsyncOpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            model = "llama-3.3-70b-versatile"
        else:
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            model = settings.openai_model

        full_response = []
        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                temperature=0.3,
                max_tokens=600,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_response.append(delta.content)
                    yield f"data: {delta.content.replace(chr(10), '<br>')}\n\n"

        except Exception as exc:
            logger.error("assistant LLM stream error: %s", exc)
            # ── Graceful fallback: structured context summary ──────────────
            # When the LLM endpoint is unreachable (firewall, network issue),
            # parse the context block and return the key facts as readable text.
            full_response = []
            fallback = _build_fallback_response(context_block, question)
            for chunk in fallback:
                full_response.append(chunk)
                yield f"data: {chunk.replace(chr(10), '<br>')}\n\n"

        finally:
            if full_response:
                assistant_text = "".join(full_response)
                try:
                    db.add(AssistantMessageDB(
                        user_id=current_user.id,
                        role="assistant",
                        content=assistant_text,
                    ))
                    db.commit()
                except Exception:
                    pass
            yield "data: [DONE]\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.get("/history")
async def get_history(
    limit: int = 40,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return recent chat messages (newest last) for display in the widget."""
    from sqlalchemy import desc
    msgs = (
        db.query(AssistantMessageDB)
        .filter_by(user_id=current_user.id)
        .order_by(desc(AssistantMessageDB.created_at))
        .limit(limit)
        .all()
    )
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "created_at": m.created_at.isoformat() + "Z",
        }
        for m in reversed(msgs)
    ]


@router.delete("/history", status_code=204)
async def clear_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clear the current user's chat history."""
    db.query(AssistantMessageDB).filter_by(user_id=current_user.id).delete()
    db.commit()
