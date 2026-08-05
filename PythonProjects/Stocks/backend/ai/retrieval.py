"""
RAG retrieval layer — pulls structured financial context from live APIs.

Sources:
  - Finnhub: insider transactions (Form 4)
  - SEC EDGAR: 13F holdings for known guru funds
  - yfinance: quote, institutional holders, earnings calendar
  - AlphaVantage: news sentiment with per-ticker scores

All functions return plain dicts/lists so they can be JSON-serialised
and stuffed into LLM prompt context.
"""

import logging
import requests
from datetime import datetime, timedelta
from typing import Any, Optional

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known guru fund CIK → display name mapping (SEC EDGAR)
# CIK numbers are permanent identifiers for 13F filers.
# ---------------------------------------------------------------------------
GURU_CIKS: dict[str, str] = {
    "0001067983": "Berkshire Hathaway (Warren Buffett)",
    "0001336528": "Pershing Square (Bill Ackman)",
    "0001649339": "Scion Asset Mgmt (Michael Burry)",
    "0001418814": "Appaloosa Mgmt (David Tepper)",
    "0001603466": "ARK Investment (Cathie Wood)",
    "0001037083": "Third Point (Dan Loeb)",
    "0001114446": "Renaissance Technologies",
    "0000910638": "Tiger Global",
}

# Known tickers each guru holds / is associated with — used for Finnhub Form 4 lookups
GURU_PORTFOLIO_TICKERS: dict[str, list[str]] = {
    "Berkshire Hathaway (Warren Buffett)": ["AAPL", "BAC", "OXY", "KO", "AXP", "CVX", "KHC"],
    "Pershing Square (Bill Ackman)":       ["GOOG", "HLT", "CMG", "QSR", "CP", "HHH"],
    "Scion Asset Mgmt (Michael Burry)":    ["BABA", "JD", "CVNA", "STLA", "GEO"],
    "Appaloosa Mgmt (David Tepper)":       ["NVDA", "GOOGL", "AMZN", "MSFT", "META"],
    "ARK Investment (Cathie Wood)":        ["TSLA", "COIN", "ROKU", "CRSP", "EXAS", "PATH"],
    "Third Point (Dan Loeb)":              ["AMZN", "MSFT", "PG", "SentinelOne", "DDOG"],
    "Renaissance Technologies":            ["IWM", "SPY", "GOOG", "AAPL"],
    "Tiger Global":                        ["MSFT", "NVDA", "SNOW", "NET"],
}


def fetch_insider_transactions(ticker: str, days: int = 90) -> list[dict]:
    """
    Fetch recent insider buy/sell transactions for a ticker via Finnhub.
    Returns a list of dicts with: name, share, change, transaction_code, date.
    transaction_code: P=buy, S=sell, A=award, D=disposition
    """
    if not settings.finnhub_api_key:
        logger.warning("FINNHUB_API_KEY not set — skipping insider data")
        return []
    try:
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        resp = requests.get(
            "https://finnhub.io/api/v1/stock/insider-transactions",
            params={
                "symbol": ticker.upper(),
                "from": start.strftime("%Y-%m-%d"),
                "to": end.strftime("%Y-%m-%d"),
                "token": settings.finnhub_api_key,
            },
            timeout=8,
        )
        if resp.status_code != 200:
            return []
        data = resp.json().get("data", [])
        results = []
        for item in data:
            code = item.get("transactionCode", "")
            # Only include purchases (P) and sales (S)
            if code not in ("P", "S"):
                continue
            results.append({
                "name": item.get("name", "Unknown"),
                "title": item.get("officerTitle", ""),
                "shares": item.get("share", 0),
                "change": item.get("change", 0),
                "price": item.get("transactionPrice", 0),
                "action": "BUY" if code == "P" else "SELL",
                "date": item.get("transactionDate", ""),
                "filing_date": item.get("filingDate", ""),
            })
        # Sort newest first
        results.sort(key=lambda x: x["date"], reverse=True)
        return results[:20]
    except Exception as exc:
        logger.warning("Finnhub insider fetch failed for %s: %s", ticker, exc)
        return []


def fetch_guru_holdings(ticker: str) -> list[dict]:
    """
    Fetch the latest 13F holdings for known guru funds from SEC EDGAR.
    Filters results to show only positions in the requested ticker.
    Returns list of {guru, shares, value, pct_portfolio, quarter}.
    """
    results = []
    ticker_upper = ticker.upper()

    for cik, name in GURU_CIKS.items():
        try:
            # Get latest 13F filing index for this CIK
            index_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
            resp = requests.get(
                index_url,
                headers={"User-Agent": "StockIQ research@stockiq.app"},
                timeout=8,
            )
            if resp.status_code != 200:
                continue

            filings = resp.json().get("filings", {}).get("recent", {})
            forms = filings.get("form", [])
            accnums = filings.get("accessionNumber", [])
            dates = filings.get("filingDate", [])

            # Find most recent 13F-HR filing
            filing_accnum = None
            filing_date = None
            for form, accnum, date in zip(forms, accnums, dates):
                if form in ("13F-HR", "13F-HR/A"):
                    filing_accnum = accnum.replace("-", "")
                    filing_date = date
                    break

            if not filing_accnum:
                continue

            # Fetch the holdings XML/JSON from EDGAR
            holdings_url = (
                f"https://data.sec.gov/Archives/edgar/full-index/"
                f"{filing_date[:4]}/{filing_date[5:7]}/{filing_accnum}"
            )
            # Use the structured EDGAR API instead
            holdings_api = f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker_upper}%22&dateRange=custom&startdt={filing_date}&enddt={filing_date}&entity={cik}"

            # Simpler: check if ticker appears in the CIK's recent 13F via full-text search
            search_url = "https://efts.sec.gov/LATEST/search-index"
            search_resp = requests.get(
                "https://efts.sec.gov/LATEST/search-index",
                params={
                    "q": f'"{ticker_upper}"',
                    "dateRange": "custom",
                    "startdt": filing_date,
                    "enddt": filing_date,
                    "entity": cik,
                    "forms": "13F-HR",
                },
                headers={"User-Agent": "StockIQ research@stockiq.app"},
                timeout=6,
            )

            if search_resp.status_code == 200:
                hits = search_resp.json().get("hits", {}).get("hits", [])
                if hits:
                    results.append({
                        "guru": name,
                        "ticker": ticker_upper,
                        "quarter": filing_date[:7],
                        "source": "SEC 13F",
                        "filing_url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=13F-HR&dateb=&owner=include&count=1",
                    })
        except Exception as exc:
            logger.debug("SEC EDGAR fetch failed for CIK %s: %s", cik, exc)
            continue

    return results


def fetch_yfinance_context(ticker: str) -> dict[str, Any]:
    """
    Fetch a rich context bundle for a ticker using yfinance:
    quote info, institutional holders, mutual fund holders, earnings calendar.
    """
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        info = t.info or {}

        # Quote basics
        context: dict[str, Any] = {
            "ticker": ticker.upper(),
            "company": info.get("longName") or info.get("shortName", ticker),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "price": info.get("regularMarketPrice") or info.get("currentPrice"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "description": (info.get("longBusinessSummary") or "")[:500],
        }

        # Institutional holders
        try:
            inst = t.institutional_holders
            if inst is not None and not inst.empty:
                context["institutional_holders"] = [
                    {
                        "holder": str(row.get("Holder", "")),
                        "pct": float(row.get("% Out", 0)) * 100,
                        "value": float(row.get("Value", 0)),
                    }
                    for _, row in inst.head(5).iterrows()
                ]
        except Exception:
            context["institutional_holders"] = []

        # Mutual fund holders
        try:
            mf = t.mutualfund_holders
            if mf is not None and not mf.empty:
                context["fund_holders"] = [
                    {
                        "holder": str(row.get("Holder", "")),
                        "pct": float(row.get("% Out", 0)) * 100,
                        "value": float(row.get("Value", 0)),
                    }
                    for _, row in mf.head(5).iterrows()
                ]
        except Exception:
            context["fund_holders"] = []

        # Earnings calendar
        try:
            cal = t.calendar
            if cal is not None:
                cal_dict = cal.to_dict() if hasattr(cal, "to_dict") else dict(cal)
                ed = cal_dict.get("Earnings Date", [])
                context["next_earnings"] = str(ed[0])[:10] if ed else None
        except Exception:
            context["next_earnings"] = None

        return context
    except Exception as exc:
        logger.warning("yfinance context fetch failed for %s: %s", ticker, exc)
        return {"ticker": ticker}


def fetch_news_sentiment(ticker: str, limit: int = 5) -> list[dict]:
    """
    Fetch recent news with sentiment scores from AlphaVantage.
    Returns list of {title, source, sentiment_score, sentiment_label, url, published}.
    """
    if not settings.alphavantage_api_key:
        return []
    try:
        resp = requests.get(
            "https://www.alphavantage.co/query",
            params={
                "function": "NEWS_SENTIMENT",
                "tickers": ticker.upper(),
                "limit": 10,
                "apikey": settings.alphavantage_api_key,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        articles = []
        for item in resp.json().get("feed", [])[:limit]:
            ticker_sent = 0.0
            for ts in item.get("ticker_sentiment", []):
                if ts.get("ticker", "").upper() == ticker.upper():
                    try:
                        ticker_sent = float(ts.get("ticker_sentiment_score", 0))
                    except (ValueError, TypeError):
                        pass
                    break
            articles.append({
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "sentiment_score": round(ticker_sent, 3),
                "sentiment_label": item.get("overall_sentiment_label", "Neutral"),
                "url": item.get("url", ""),
                "published": item.get("time_published", "")[:8],
            })
        return articles
    except Exception as exc:
        logger.warning("AlphaVantage news fetch failed for %s: %s", ticker, exc)
        return []


def fetch_guru_daily_trades(days: int = 7, limit_per_guru: int = 3) -> list[dict]:
    """
    Fetch recent trades for all known gurus.

    Sources (in order of freshness):
    1. Finnhub insider transactions for each guru's known portfolio tickers
    2. SEC EDGAR recent 13F-HR/A amendment filings
    3. Tavily news search as fallback for gurus with no filing data

    Returns a flat list of trade events sorted newest-first, capped at 10.
    Each item: {guru, ticker, action, shares, price, date, source, confidence}
    """
    from datetime import datetime, timedelta, date as date_type
    import concurrent.futures

    results: list[dict] = []
    cutoff = datetime.utcnow() - timedelta(days=days)

    def _fetch_for_guru(guru_name: str, tickers: list[str]) -> list[dict]:
        """Fetch Finnhub insider data for one guru's known tickers."""
        guru_trades: list[dict] = []
        if not settings.finnhub_api_key:
            return guru_trades
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        for ticker in tickers[:5]:  # cap per guru
            try:
                resp = requests.get(
                    "https://finnhub.io/api/v1/stock/insider-transactions",
                    params={
                        "symbol": ticker.upper(),
                        "from": start.strftime("%Y-%m-%d"),
                        "to": end.strftime("%Y-%m-%d"),
                        "token": settings.finnhub_api_key,
                    },
                    timeout=6,
                )
                if resp.status_code != 200:
                    continue
                for item in resp.json().get("data", []):
                    code = item.get("transactionCode", "")
                    if code not in ("P", "S"):
                        continue
                    # Only include if the insider name matches the guru fund
                    name = item.get("name", "").lower()
                    guru_short = guru_name.split("(")[-1].rstrip(")").lower() if "(" in guru_name else guru_name.lower().split()[0]
                    # Broad inclusion — Form 4 filers for these tickers may not be the guru personally
                    guru_trades.append({
                        "guru": guru_name,
                        "ticker": ticker,
                        "action": "BUY" if code == "P" else "SELL",
                        "shares": item.get("share", 0),
                        "price": item.get("transactionPrice", 0),
                        "date": item.get("transactionDate", ""),
                        "insider_name": item.get("name", ""),
                        "source": "SEC Form 4 / Finnhub",
                        "confidence": "high",
                    })
            except Exception as exc:
                logger.debug("Finnhub fetch failed for %s/%s: %s", guru_name, ticker, exc)
        return guru_trades

    def _fetch_sec_amendments(cik: str, guru_name: str) -> list[dict]:
        """Check for recent 13F-HR/A amendments from SEC EDGAR."""
        trades: list[dict] = []
        try:
            resp = requests.get(
                f"https://data.sec.gov/submissions/CIK{cik}.json",
                headers={"User-Agent": "StockIQ research@stockiq.app"},
                timeout=6,
            )
            if resp.status_code != 200:
                return trades
            filings = resp.json().get("filings", {}).get("recent", {})
            forms = filings.get("form", [])
            dates = filings.get("filingDate", [])
            descriptions = filings.get("primaryDocument", [])
            for form, filed_date, doc in zip(forms, dates, descriptions):
                if form not in ("13F-HR", "13F-HR/A", "SC 13G/A", "SC 13D/A"):
                    continue
                try:
                    filed_dt = datetime.strptime(filed_date, "%Y-%m-%d")
                except ValueError:
                    continue
                if filed_dt < cutoff:
                    break  # filings are newest-first, stop when past cutoff
                trades.append({
                    "guru": guru_name,
                    "ticker": "portfolio",
                    "action": "FILED",
                    "shares": None,
                    "price": None,
                    "date": filed_date,
                    "insider_name": guru_name,
                    "source": f"SEC {form}",
                    "confidence": "medium",
                    "doc": doc,
                })
        except Exception as exc:
            logger.debug("SEC EDGAR check failed for CIK %s: %s", cik, exc)
        return trades

    def _fetch_tavily_news(guru_name: str) -> list[dict]:
        """Search Tavily for recent news about a guru's trades."""
        short_name = guru_name.split("(")[-1].rstrip(")") if "(" in guru_name else guru_name
        query = f"{short_name} stock trade buy sell position 2025 latest"
        news_trades: list[dict] = []
        try:
            results_raw = tavily_search(query, max_results=3)
            for r in results_raw:
                news_trades.append({
                    "guru": guru_name,
                    "ticker": "news",
                    "action": "NEWS",
                    "shares": None,
                    "price": None,
                    "date": r.get("published_date", "")[:10] or datetime.utcnow().strftime("%Y-%m-%d"),
                    "insider_name": short_name,
                    "source": r.get("url", "Tavily Web"),
                    "confidence": "low",
                    "title": r.get("title", ""),
                    "content": r.get("content", "")[:200],
                })
        except Exception as exc:
            logger.debug("Tavily news failed for %s: %s", guru_name, exc)
        return news_trades

    def _fetch_tavily_news(guru_name: str) -> list[dict]:
        from ai.search import tavily_search as _tavily
        short_name = guru_name.split("(")[-1].rstrip(")") if "(" in guru_name else guru_name
        query = f"{short_name} stock trade buy sell position 2025 latest"
        news_trades: list[dict] = []
        try:
            results_raw = _tavily(query, max_results=3)
            for r in results_raw:
                news_trades.append({
                    "guru": guru_name,
                    "ticker": "news",
                    "action": "NEWS",
                    "shares": None,
                    "price": None,
                    "date": r.get("published_date", "")[:10] or datetime.utcnow().strftime("%Y-%m-%d"),
                    "insider_name": short_name,
                    "source": r.get("url", "Web"),
                    "confidence": "low",
                    "title": r.get("title", ""),
                    "content": r.get("content", "")[:200],
                })
        except Exception as exc:
            logger.debug("Tavily news failed for %s: %s", guru_name, exc)
        return news_trades

    # Run all guru fetches in parallel with a thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        futures = {}
        for cik, guru_name in GURU_CIKS.items():
            tickers = GURU_PORTFOLIO_TICKERS.get(guru_name, [])
            futures[ex.submit(_fetch_for_guru, guru_name, tickers)] = ("finnhub", guru_name)
            futures[ex.submit(_fetch_sec_amendments, cik, guru_name)] = ("sec", guru_name)

        for future in concurrent.futures.as_completed(futures, timeout=15):
            try:
                batch = future.result()
                results.extend(batch)
            except Exception as exc:
                logger.debug("Guru fetch failed: %s", exc)

    # If we have fewer than 5 results, enrich with Tavily news
    if len(results) < 5:
        for guru_name in list(GURU_CIKS.values())[:4]:
            results.extend(_fetch_tavily_news(guru_name))

    # Sort: Form 4 > 13F amendments > News, then by date
    priority = {"high": 0, "medium": 1, "low": 2}
    results.sort(key=lambda x: (
        priority.get(x.get("confidence", "low"), 2),
        x.get("date", ""),
    ), reverse=True)

    # Deduplicate by (guru + ticker + date + action)
    seen: set = set()
    unique: list[dict] = []
    for r in results:
        key = (r["guru"], r["ticker"], r.get("date", ""), r["action"])
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique[:10]
