"""
AI Research API router.

Endpoints
---------
POST /ai/analyze/{ticker}      — stream full RAG analysis (SSE)
GET  /ai/insiders/{ticker}     — structured insider transaction data
POST /ai/insiders/{ticker}/analyze — stream insider-focused AI analysis
GET  /ai/gurus/{ticker}        — institutional + guru 13F holdings

All endpoints require a valid JWT Bearer token.
"""

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from auth.models import User
from dependencies import get_current_user
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_ai_service():
    """Dependency — instantiate AIService, raise 503 if no LLM is configured."""
    from fastapi import HTTPException, status
    if not settings.openai_api_key and not settings.groq_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI features require OPENAI_API_KEY or GROQ_API_KEY to be configured.",
        )
    from ai.service import AIService
    return AIService()


# ---------------------------------------------------------------------------
# POST /ai/analyze/{ticker}  — streaming SSE
# ---------------------------------------------------------------------------

class AnalyzeRequest:
    pass

from pydantic import BaseModel

class AnalyzeBody(BaseModel):
    question: str = "Who are the biggest buyers of this stock? What are major investors and insiders doing?"


@router.post("/analyze/{ticker}")
async def analyze_ticker(
    ticker: str,
    body: AnalyzeBody = AnalyzeBody(),
    current_user: User = Depends(get_current_user),
    service=Depends(_get_ai_service),
):
    """
    Stream a full AI research analysis for a ticker using RAG.

    Pulls context from:
    - yfinance (quote, holders, earnings)
    - Finnhub (insider Form 4 transactions)
    - AlphaVantage (news sentiment)
    - Tavily (real-time web search)

    Returns a Server-Sent Events stream of text chunks.
    """
    async def event_stream():
        try:
            async for chunk in service.stream_analysis(ticker.upper(), body.question):
                # SSE format: data: <content>\n\n
                yield f"data: {json.dumps({'text': chunk})}\n\n"
        except Exception as exc:
            logger.error("Analysis stream error for %s: %s", ticker, exc)
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ---------------------------------------------------------------------------
# GET /ai/insiders/{ticker}  — structured data
# ---------------------------------------------------------------------------

@router.get("/insiders/{ticker}")
async def get_insiders(
    ticker: str,
    current_user: User = Depends(get_current_user),
    service=Depends(_get_ai_service),
):
    """
    Return structured insider transaction data for the past 180 days.
    Includes a net-signal summary (bullish / bearish / neutral).
    """
    return await service.get_insiders(ticker.upper())


# ---------------------------------------------------------------------------
# POST /ai/insiders/{ticker}/analyze  — streaming SSE
# ---------------------------------------------------------------------------

@router.post("/insiders/{ticker}/analyze")
async def analyze_insiders(
    ticker: str,
    current_user: User = Depends(get_current_user),
    service=Depends(_get_ai_service),
):
    """Stream an AI analysis focused exclusively on insider transactions."""

    async def event_stream():
        try:
            async for chunk in service.stream_insider_analysis(ticker.upper()):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# POST /ai/buyers/{ticker}  — who is buying from news + filings (streaming SSE)
# ---------------------------------------------------------------------------


@router.post("/buyers/{ticker}")
async def analyze_buyers(
    ticker: str,
    current_user: User = Depends(get_current_user),
    service=Depends(_get_ai_service),
):
    """
    Stream a targeted AI analysis answering: 'Who are the top individual
    buyers of this stock right now?'

    Sources:
    - Finnhub Form 4 insider transactions (last 6 months)
    - yfinance institutional + mutual fund holders
    - 6 parallel Tavily web searches for latest buyer news
    - GPT-4o synthesises and ranks named buyers with evidence
    """

    async def event_stream():
        try:
            async for chunk in service.stream_buyers_analysis(ticker.upper()):
                yield f"data: {json.dumps({'text': chunk})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GET /ai/gurus/{ticker}  — institutional + 13F guru holdings
# ---------------------------------------------------------------------------

@router.get("/gurus/{ticker}")
async def get_gurus(
    ticker: str,
    current_user: User = Depends(get_current_user),
    service=Depends(_get_ai_service),
):
    """
    Return institutional holders, mutual fund holders, and SEC 13F
    guru fund presence for a ticker.
    """
    return await service.get_gurus(ticker.upper())


# ---------------------------------------------------------------------------
# GET /ai/guru-trades  — top 10 guru daily trades for dashboard
# ---------------------------------------------------------------------------


@router.get("/guru-trades")
async def get_guru_trades(
    days: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
):
    """
    Return up to 10 of the most recent trades/filings from known stock gurus.

    Sources:
    - Finnhub Form 4 insider data for each guru's known portfolio tickers
    - SEC EDGAR 13F-HR/A amendments (portfolio change filings)
    - Tavily news as fallback when no filing data is available

    Cached for 1 hour. Never raises — returns empty list on failure.
    """
    import asyncio
    from ai.retrieval import fetch_guru_daily_trades

    loop = asyncio.get_event_loop()
    try:
        trades = await loop.run_in_executor(None, fetch_guru_daily_trades, days, 3)
    except Exception as exc:
        logger.warning("guru-trades fetch failed: %s", exc)
        trades = []
    return {"trades": trades, "days": days}
