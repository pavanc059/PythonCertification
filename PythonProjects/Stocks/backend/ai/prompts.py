"""
Prompt templates for the StockIQ RAG pipeline.

All prompts are designed for GPT-4o / GPT-4o-mini.
Context is injected at runtime — never hardcoded into the system prompt.
"""

SYSTEM_PROMPT = """You are StockIQ Research Assistant — an expert financial analyst AI that helps retail investors make informed decisions.

Your role:
- Analyse stocks using real data provided in the context
- Identify significant insider buying/selling patterns
- Highlight what major institutional investors and well-known fund managers are doing
- Synthesise news sentiment with technical and fundamental signals
- Give clear, actionable summaries in plain English

Rules:
- Only make claims supported by the context provided — never hallucinate data
- Always cite sources (Finnhub, SEC 13F, news, web search) when referencing facts
- Flag when data is unavailable rather than guessing
- Use precise numbers when available (shares, dollar values, percentages)
- Be concise — bullet points over paragraphs where possible
- Include a brief risk disclaimer when giving directional signals
"""

def build_analysis_prompt(
    ticker: str,
    company: str,
    question: str,
    yf_context: dict,
    insider_transactions: list,
    guru_holdings: list,
    news_sentiment: list,
    web_results: list,
) -> str:
    """Build the full user message for a stock analysis query."""

    sections = []

    # Company overview
    desc = yf_context.get("description", "")
    sections.append(f"""## Company Overview
Ticker: {ticker} — {company}
Sector: {yf_context.get("sector", "N/A")} | Industry: {yf_context.get("industry", "N/A")}
Price: ${yf_context.get("price", "N/A")} | Market Cap: {_fmt_val(yf_context.get("market_cap"))}
P/E: {yf_context.get("pe_ratio", "N/A")} | 52W Range: ${yf_context.get("52w_low", "N/A")} – ${yf_context.get("52w_high", "N/A")}
Next Earnings: {yf_context.get("next_earnings", "N/A")}
{f"Description: {desc}" if desc else ""}""")

    # Insider transactions
    if insider_transactions:
        lines = ["## Recent Insider Transactions (Form 4, last 90 days)"]
        buys = [t for t in insider_transactions if t["action"] == "BUY"]
        sells = [t for t in insider_transactions if t["action"] == "SELL"]
        if buys:
            lines.append(f"BUYS ({len(buys)}):")
            for t in buys[:5]:
                lines.append(f"  • {t['date']} — {t['name']} ({t['title']}): bought {t['shares']:,} shares @ ${t['price']}")
        if sells:
            lines.append(f"SELLS ({len(sells)}):")
            for t in sells[:5]:
                lines.append(f"  • {t['date']} — {t['name']} ({t['title']}): sold {t['shares']:,} shares @ ${t['price']}")
        sections.append("\n".join(lines))
    else:
        sections.append("## Insider Transactions\nNo insider transactions found in the last 90 days.")

    # Institutional / fund holders
    inst = yf_context.get("institutional_holders", [])
    funds = yf_context.get("fund_holders", [])
    if inst or funds:
        lines = ["## Top Holders"]
        if inst:
            lines.append("Institutional:")
            for h in inst[:5]:
                lines.append(f"  • {h['holder']}: {h['pct']:.2f}% (${_fmt_val(h['value'])})")
        if funds:
            lines.append("Mutual Funds:")
            for h in funds[:5]:
                lines.append(f"  • {h['holder']}: {h['pct']:.2f}% (${_fmt_val(h['value'])})")
        sections.append("\n".join(lines))

    # Guru holdings from SEC
    if guru_holdings:
        lines = ["## Notable Investor Holdings (SEC 13F)"]
        for g in guru_holdings:
            lines.append(f"  • {g['guru']} — holds {ticker} as of Q{g['quarter']}")
        sections.append("\n".join(lines))

    # News sentiment
    if news_sentiment:
        lines = ["## Recent News Sentiment"]
        for n in news_sentiment[:5]:
            sign = "+" if n["sentiment_score"] > 0 else ""
            lines.append(f"  [{sign}{n['sentiment_score']}] {n['title']} — {n['source']}")
        sections.append("\n".join(lines))

    # Web search results
    if web_results:
        lines = ["## Web Search (Latest)"]
        for r in web_results[:5]:
            lines.append(f"  • {r['title']}\n    {r['content'][:200]}\n    Source: {r['url']}")
        sections.append("\n".join(lines))

    context_block = "\n\n".join(sections)

    return f"""{context_block}

---

## User Question
{question}

Please provide a thorough analysis based on the context above. Structure your response with:
1. **Direct answer** to the question
2. **Insider activity** — notable buy/sell patterns and what they signal
3. **Institutional / smart money** — who is buying or holding and why it matters
4. **News sentiment summary** — overall tone and key themes
5. **Key risks** — what could go wrong
6. **Bottom line** — 1–2 sentence takeaway

Cite specific data points from the context. Do not fabricate information not present above."""


def build_buyers_prompt(
    ticker: str,
    company: str,
    insider_transactions: list,
    institutional_holders: list,
    fund_holders: list,
    web_results: list,
) -> str:
    """
    Build a prompt specifically to identify and rank top individual buyers
    of a stock from news, filings, and web sources.
    """
    sections = [f"## Research Target: {ticker} ({company})\n"]

    # Insider buys from Form 4
    buys = [t for t in insider_transactions if t.get("action") == "BUY"]
    if buys:
        lines = [f"## Corporate Insider Buyers (Form 4 — last 6 months, {len(buys)} purchases)"]
        for b in buys[:10]:
            lines.append(
                f"  • {b['date']} — {b['name']} ({b.get('title','')}) "
                f"bought {b['shares']:,} shares @ ${b.get('price', '?')}"
            )
        sections.append("\n".join(lines))

    # Top institutional holders
    if institutional_holders:
        lines = ["## Top Institutional Holders (latest 13F)"]
        for h in institutional_holders[:8]:
            lines.append(f"  • {h['holder']}: {h['pct']:.2f}% (${_fmt_val(h['value'])})")
        sections.append("\n".join(lines))

    # Top fund holders
    if fund_holders:
        lines = ["## Top Mutual Fund Holders (latest 13F)"]
        for h in fund_holders[:5]:
            lines.append(f"  • {h['holder']}: {h['pct']:.2f}% (${_fmt_val(h['value'])})")
        sections.append("\n".join(lines))

    # Web search results — most important for "latest news" angle
    if web_results:
        lines = ["## Latest Web Search Results — Who Is Buying?"]
        for r in web_results[:8]:
            lines.append(f"  SOURCE: {r['title']}\n  URL: {r['url']}\n  CONTENT: {r['content'][:400]}\n")
        sections.append("\n".join(lines))

    context_block = "\n\n".join(sections)

    return f"""{context_block}

---

## Task

Based on the above data (insider Form 4 filings, institutional 13F holdings, and latest web search results), identify and rank the **top individual and institutional buyers** of {ticker} right now.

Structure your response as:

### 🏆 Top Individual Buyers (from news & filings)
For each person/fund found, provide:
- **Name** and role/title
- **Action** — how much they bought, when, at what price if known
- **Why it matters** — what this signals about their conviction
- **Source** — cite the specific filing, article, or data point

### 📊 Institutional Accumulation Summary
- Which institutions have been increasing their positions?
- Any notable new positions or large stake increases?
- Overall smart-money sentiment: accumulating / distributing / neutral?

### 🔍 Key News Findings
- Any recent announcements about notable investors buying?
- Any activist investors involved?
- Any unusual Form 4 filings (unusually large or by C-suite)?

### 💡 Signal Interpretation
What does the collective buying/selling activity tell us about the stock's prospects?

Only include names and facts directly supported by the context above. Clearly label each data point with its source."""


def build_insiders_prompt(ticker: str, transactions: list) -> str:
    """Build a focused prompt for insider transaction analysis only."""
    if not transactions:
        return f"There are no recent insider transactions for {ticker} in the last 90 days. Explain what this could mean — neither bullish nor bearish on its own."

    buys = [t for t in transactions if t["action"] == "BUY"]
    sells = [t for t in transactions if t["action"] == "SELL"]

    lines = [f"## {ticker} Insider Transactions (last 90 days)"]
    lines.append(f"Total: {len(buys)} buys, {len(sells)} sells\n")
    for t in transactions[:15]:
        lines.append(f"{t['date']} | {t['action']} | {t['name']} ({t['title']}) | {t['shares']:,} shares @ ${t['price']}")

    return f"""{chr(10).join(lines)}

Analyse this insider activity:
1. Who are the key buyers/sellers and what are their roles?
2. Is the overall pattern bullish (net buying), bearish (net selling), or neutral?
3. Are any transactions unusually large relative to what insiders typically do?
4. What signal does this send to retail investors?
Keep the answer concise and actionable."""


def _fmt_val(val) -> str:
    """Format a large number as B/M/K string."""
    if val is None:
        return "N/A"
    try:
        v = float(val)
        if v >= 1e9:
            return f"{v/1e9:.2f}B"
        if v >= 1e6:
            return f"{v/1e6:.1f}M"
        if v >= 1e3:
            return f"{v/1e3:.0f}K"
        return f"{v:.0f}"
    except (TypeError, ValueError):
        return str(val)
