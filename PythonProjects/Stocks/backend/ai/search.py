"""
Tavily web search wrapper for real-time financial research.

Builds targeted search queries from ticker context and returns
clean extracted results ready to be injected into LLM prompts.
"""

import logging
from typing import Optional
from config import settings

logger = logging.getLogger(__name__)


def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    """
    Run a Tavily search and return clean results.
    Each result: {title, url, content (snippet), published_date, score}.
    Returns [] if TAVILY_API_KEY is not set or on any error.
    """
    if not settings.tavily_api_key:
        logger.warning("TAVILY_API_KEY not set — skipping web search")
        return []
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(
            query=query,
            search_depth="advanced",
            max_results=max_results,
            include_answer=False,
            include_raw_content=False,
        )
        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:600],  # cap snippet length
                "published_date": r.get("published_date", ""),
                "score": round(r.get("score", 0), 3),
            })
        return results
    except Exception as exc:
        logger.warning("Tavily search failed for '%s': %s", query, exc)
        return []


def build_queries(ticker: str, company: str, question: Optional[str] = None) -> list[str]:
    """
    Generate a set of targeted search queries for a ticker research session.
    If a user question is provided, it is added as a direct query.
    """
    queries = [
        f"{ticker} {company} insider buying 2025",
        f"{ticker} hedge fund institutional investor positions 2025",
        f"{ticker} Warren Buffett Cathie Wood Michael Burry holdings",
        f"{ticker} {company} stock analysis latest news",
    ]
    if question:
        queries.insert(0, f"{ticker} {company} {question}")
    return queries


def build_buyer_queries(ticker: str, company: str) -> list[str]:
    """
    Targeted queries specifically to find top individual and institutional
    buyers from recent news, filings, and social/financial media.
    """
    return [
        f"who is buying {ticker} stock 2025 latest news",
        f"{ticker} {company} largest buyers accumulating shares 2025",
        f"{ticker} insider purchase Form 4 SEC 2025",
        f"{company} stock bought by fund manager investor 2025",
        f"{ticker} activist investor stake position increased",
        f"who bought {ticker} recently hedge fund 13F",
    ]
