"""
AIService — orchestrates the RAG pipeline for stock research queries.

Flow:
  1. Parallel retrieval: yfinance context + Finnhub insiders + news sentiment
  2. Tavily web search for real-time grounding
  3. Prompt assembly
  4. OpenAI GPT-4o streaming response
"""

import asyncio
import logging
from typing import AsyncGenerator, Optional

from config import settings
from ai.retrieval import (
    fetch_insider_transactions,
    fetch_guru_holdings,
    fetch_yfinance_context,
    fetch_news_sentiment,
)
from ai.search import tavily_search, build_queries, build_buyer_queries
from ai.prompts import (
    SYSTEM_PROMPT,
    build_analysis_prompt,
    build_buyers_prompt,
    build_insiders_prompt,
)

logger = logging.getLogger(__name__)


class AIService:

    # ---------------------------------------------------------------------------
    # Support multiple LLM backends via OpenAI-compatible API:
    #   - OpenAI:  set OPENAI_API_KEY
    #   - Groq:    set GROQ_API_KEY  (free, fast, Llama 3.3 70B)
    # Groq is used as fallback if OPENAI_API_KEY is not reachable.
    # ---------------------------------------------------------------------------
    def __init__(self) -> None:
        from openai import AsyncOpenAI
        if settings.groq_api_key:
            self.client = AsyncOpenAI(
                api_key=settings.groq_api_key,
                base_url="https://api.groq.com/openai/v1",
            )
            self.model = "llama-3.3-70b-versatile"
            logger.info("AIService using Groq (Llama 3.3 70B)")
        elif settings.openai_api_key:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            self.model = settings.openai_model
            logger.info("AIService using OpenAI (%s)", self.model)
        else:
            raise ValueError("Neither OPENAI_API_KEY nor GROQ_API_KEY is configured.")

    # ------------------------------------------------------------------
    # Public: stream full analysis
    # ------------------------------------------------------------------

    async def stream_analysis(
        self,
        ticker: str,
        question: str = "Who are the biggest buyers of this stock? What are major investors doing?",
    ) -> AsyncGenerator[str, None]:
        """
        Full RAG pipeline — retrieves context then streams GPT response.
        Yields text chunks as they arrive from OpenAI.
        """
        ticker = ticker.upper()

        # 1. Parallel data retrieval (run blocking IO in thread pool)
        loop = asyncio.get_event_loop()
        yf_ctx, insiders, news = await asyncio.gather(
            loop.run_in_executor(None, fetch_yfinance_context, ticker),
            loop.run_in_executor(None, fetch_insider_transactions, ticker),
            loop.run_in_executor(None, fetch_news_sentiment, ticker, 5),
        )

        company = yf_ctx.get("company", ticker)

        # 2. Tavily web search (run in executor — blocking)
        queries = build_queries(ticker, company, question)
        web_results = []
        for q in queries[:3]:
            results = await loop.run_in_executor(None, tavily_search, q, 3)
            web_results.extend(results)

        # Deduplicate web results by URL
        seen_urls: set[str] = set()
        unique_web: list[dict] = []
        for r in web_results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                unique_web.append(r)

        # 3. Guru holdings (fast, separate)
        guru_holdings: list[dict] = []
        try:
            guru_holdings = await loop.run_in_executor(None, fetch_guru_holdings, ticker)
        except Exception as exc:
            logger.debug("Guru holdings failed: %s", exc)

        # 4. Assemble prompt
        user_message = build_analysis_prompt(
            ticker=ticker,
            company=company,
            question=question,
            yf_context=yf_ctx,
            insider_transactions=insiders,
            guru_holdings=guru_holdings,
            news_sentiment=news,
            web_results=unique_web[:8],
        )

        # 5. Stream from OpenAI
        async for chunk in self._stream_openai(user_message):
            yield chunk

    # ------------------------------------------------------------------
    # Public: stream insider-only analysis
    # ------------------------------------------------------------------

    async def stream_insider_analysis(self, ticker: str) -> AsyncGenerator[str, None]:
        """Focused analysis of insider transactions only."""
        ticker = ticker.upper()
        loop = asyncio.get_event_loop()
        insiders = await loop.run_in_executor(None, fetch_insider_transactions, ticker, 180)

        # Also do a web search for recent insider news
        web = await loop.run_in_executor(
            None, tavily_search,
            f"{ticker} insider buying selling Form 4 SEC filing 2025", 4
        )
        extra_context = ""
        if web:
            extra_context = "\n\n## Web Context\n" + "\n".join(
                f"• {r['title']}: {r['content'][:200]}" for r in web
            )

        prompt = build_insiders_prompt(ticker, insiders) + extra_context
        async for chunk in self._stream_openai(prompt):
            yield chunk

    # ------------------------------------------------------------------
    # Public: raw structured data (no AI — for data endpoints)
    # ------------------------------------------------------------------

    async def stream_buyers_analysis(self, ticker: str) -> AsyncGenerator[str, None]:
        """
        Dedicated RAG pipeline to answer: 'Who are the top individual buyers?'

        Runs 6 targeted Tavily web queries in parallel, combines with
        Finnhub insider data and institutional holders, then asks GPT-4o
        to identify, rank and explain the key buyers.
        """
        ticker = ticker.upper()
        loop = asyncio.get_event_loop()

        # Parallel: yfinance context + insiders + web search
        yf_ctx, insiders = await asyncio.gather(
            loop.run_in_executor(None, fetch_yfinance_context, ticker),
            loop.run_in_executor(None, fetch_insider_transactions, ticker, 180),
        )
        company = yf_ctx.get("company", ticker)

        # Run all buyer-focused Tavily queries in parallel
        buyer_queries = build_buyer_queries(ticker, company)
        web_tasks = [
            loop.run_in_executor(None, tavily_search, q, 4)
            for q in buyer_queries
        ]
        web_batches = await asyncio.gather(*web_tasks)

        # Flatten + deduplicate by URL
        seen_urls: set[str] = set()
        web_results: list[dict] = []
        for batch in web_batches:
            for r in batch:
                if r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    web_results.append(r)

        # Sort by Tavily relevance score
        web_results.sort(key=lambda x: x.get("score", 0), reverse=True)

        prompt = build_buyers_prompt(
            ticker=ticker,
            company=company,
            insider_transactions=insiders,
            institutional_holders=yf_ctx.get("institutional_holders", []),
            fund_holders=yf_ctx.get("fund_holders", []),
            web_results=web_results[:10],
        )

        async for chunk in self._stream_openai(prompt):
            yield chunk

    async def get_insiders(self, ticker: str) -> dict:        """Return structured insider transaction data without AI synthesis."""
        loop = asyncio.get_event_loop()
        insiders = await loop.run_in_executor(None, fetch_insider_transactions, ticker, 180)
        buys = [t for t in insiders if t["action"] == "BUY"]
        sells = [t for t in insiders if t["action"] == "SELL"]
        net_shares = sum(t["shares"] for t in buys) - sum(t["shares"] for t in sells)
        return {
            "ticker": ticker.upper(),
            "transactions": insiders,
            "summary": {
                "total_buys": len(buys),
                "total_sells": len(sells),
                "net_shares": net_shares,
                "signal": "bullish" if net_shares > 0 else "bearish" if net_shares < 0 else "neutral",
            },
        }

    async def get_gurus(self, ticker: str) -> dict:
        """Return guru 13F holdings and yfinance institutional data."""
        loop = asyncio.get_event_loop()
        yf_ctx, gurus = await asyncio.gather(
            loop.run_in_executor(None, fetch_yfinance_context, ticker),
            loop.run_in_executor(None, fetch_guru_holdings, ticker),
        )
        return {
            "ticker": ticker.upper(),
            "company": yf_ctx.get("company", ticker),
            "institutional_holders": yf_ctx.get("institutional_holders", []),
            "fund_holders": yf_ctx.get("fund_holders", []),
            "guru_13f": gurus,
        }

    # ------------------------------------------------------------------
    # Internal: OpenAI streaming
    # ------------------------------------------------------------------

    async def _stream_openai(self, user_message: str) -> AsyncGenerator[str, None]:
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                stream=True,
                temperature=0.3,
                max_tokens=2048,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta.content:
                    yield delta.content
        except Exception as exc:
            logger.error("OpenAI streaming failed: %s", exc)
            yield f"\n\n⚠️ AI analysis failed: {exc}"
