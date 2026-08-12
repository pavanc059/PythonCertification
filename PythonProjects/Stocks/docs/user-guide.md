# User Guide

**Version:** 2.0  
**Last Updated:** 2024

Welcome to StockIQ, your institutional-grade stock analysis platform. This guide will help you get started and make the most of the platform's features.

## Table of Contents

- [Getting Started](#getting-started)
- [Web Interface](#web-interface)
- [CLI Usage](#cli-usage)
- [Dashboard Features](#dashboard-features)
- [Daily Intelligence](#daily-intelligence)
- [Penny Stock Dashboard](#penny-stock-dashboard)
- [News Feed](#news-feed)
- [Portfolio Management](#portfolio-management)
- [Alerts and Notifications](#alerts-and-notifications)
- [Custom Screeners](#custom-screeners)
- [Backtesting](#backtesting)
- [Paper Trading](#paper-trading)
- [Tips and Best Practices](#tips-and-best-practices)

---

## Getting Started

### Accessing the Platform

**Web Interface:**  
Open your browser and navigate to: http://localhost:8501

**Command Line:**  
Run from terminal:
```bash
python stock_analyzer.py AAPL
```

### First-Time Setup

1. **Create a Watchlist**
   - Navigate to "Portfolio & Watchlist" in the sidebar
   - Click "Add to Watchlist"
   - Enter ticker symbols (e.g., AAPL, TSLA, MSFT)

2. **Configure Alerts**
   - Go to "Alerts & Notifications"
   - Set price alerts for key stocks
   - Configure news alerts for your watchlist

3. **Customize Dashboard**
   - Visit "Dashboard Settings"
   - Choose which widgets to display
   - Arrange layout to your preference

---

## Web Interface

### Navigation

The web interface uses a sidebar navigation with the following sections:

- **🏠 Home** - Daily Market Brief dashboard
- **📊 Markets** - Market overview and top movers
- **💰 Penny Stocks** - Penny stock momentum tracker
- **📰 News** - Real-time news feed
- **📈 Analysis** - Individual stock analysis
- **💼 Portfolio** - Portfolio management and watchlist
- **⚠️ Alerts** - Alert configuration and history
- **🔍 Screener** - Custom stock screener
- **📉 Backtest** - Strategy backtesting
- **📄 Reports** - Daily reports and summaries


### Interface Features

**Responsive Design:**  
The interface adapts to different screen sizes - works on desktop, tablet, and mobile browsers.

**Dark/Light Mode:**  
Toggle theme in the sidebar settings.

**Real-Time Updates:**  
Data refreshes automatically during market hours without page reload.

**Export Options:**  
Download charts as PNG, data as CSV, or reports as PDF from any page.

---

## CLI Usage

### Basic Stock Analysis

Analyze a single stock:

```bash
python stock_analyzer.py AAPL
```

**Output includes:**
- Current price and change
- Technical indicators (RSI, MACD, Bollinger Bands)
- Fundamental metrics (P/E ratio, EPS, market cap)
- Sentiment analysis (news and social media)
- ML price prediction with confidence score
- SHAP feature importance

### Advanced Options

**Skip ML predictions:**
```bash
python stock_analyzer.py TSLA --no-ml
```

**Skip fundamental analysis:**
```bash
python stock_analyzer.py NVDA --no-fundamentals
```

**Skip sentiment analysis:**
```bash
python stock_analyzer.py MSFT --no-sentiment
```

**Combine options:**
```bash
python stock_analyzer.py GOOGL --no-ml --no-sentiment
```

### Batch Analysis

Analyze multiple stocks:

```bash
for ticker in AAPL TSLA MSFT GOOGL; do
    python stock_analyzer.py $ticker
done
```

---

## Dashboard Features

### Daily Market Brief

The default landing page providing a comprehensive market overview.

**Widgets:**

1. **Market Indices**
   - S&P 500, NASDAQ, DOW, Russell 2000
   - Real-time values and daily changes
   - Interactive charts with historical data

2. **Top Movers**
   - Top 10 gainers and losers
   - Percentage change, volume, market cap
   - Click any stock for detailed analysis

3. **Market Sentiment Gauge**
   - Overall market sentiment (-100 to +100)
   - Based on news analysis and price action
   - Color-coded indicator (red/yellow/green)

4. **Breaking News**
   - 5 most recent high-impact news stories
   - Sentiment scores and affected tickers
   - Click to read full article

5. **Daily Predictions**
   - Next-day forecasts for watchlist stocks
   - Confidence scores and price targets
   - Strong Buy / Buy / Hold / Sell ratings


6. **Sector Performance**
   - Heat map showing sector performance
   - Click sectors for detailed breakdown
   - Compare sector rotation trends

7. **Economic Calendar**
   - Today's scheduled economic events
   - Expected impact on markets
   - Links to event details

**How to Use:**

- Dashboard loads automatically when you open the app
- Data refreshes every 5 minutes during market hours
- Click any stock ticker for detailed analysis
- Customize widgets via Dashboard Settings
- Export daily summary as PDF

---

## Daily Intelligence

### Top Movers Tracker

**Location:** Markets → Top Movers

Identifies stocks with largest percentage changes.

**Features:**
- Top 20 gainers and losers
- Updates every 5 minutes during market hours
- Filters: Min market cap $100M, min volume 100K shares
- Unusual volume indicators (>3x average)

**Columns:**
- Ticker symbol
- Price and change (% and $)
- Volume and volume ratio
- Market cap and sector
- Links to detailed analysis

**Actions:**
- Click ticker for full analysis
- Add to watchlist
- Set price alert
- View news for ticker

### Market Overview

**Location:** Markets → Overview

Comprehensive market statistics and trends.

**Includes:**
- Major indices performance
- Sector heat map
- Market breadth indicators (advance/decline)
- Volume analysis
- Volatility index (VIX)

---

## Penny Stock Dashboard

**Location:** Penny Stocks → Dashboard

Dedicated tracker for penny stocks (<$5) with sudden gains.

### Features

**Scanning Criteria:**
- Price < $5.00
- Intraday gain >20% OR 5-day gain >50%
- Minimum average volume: 50,000 shares
- Updates every 2 minutes during market hours

**Display:**
- Top 20 penny stocks ranked by momentum score
- Price charts (1-day, 5-day, 30-day views)
- Volume surge indicators
- Risk assessment (low/medium/high/extreme)
- Catalyst identification (news, earnings, etc.)

**Momentum Score:**

Composite score (0-100) based on:
- Price change magnitude (40%)
- Volume surge ratio (30%)
- Trend consistency (20%)
- Catalyst presence (10%)

**Risk Metrics:**
- Liquidity risk
- Volatility risk (ATR-based)
- Bid-ask spread percentage
- Pump-and-dump detection score


**How to Use:**

1. Monitor the dashboard during market hours
2. Focus on high momentum score + low/medium risk
3. Check for legitimate catalysts (news, earnings)
4. Avoid stocks flagged with high suspicion scores
5. Set alerts for momentum threshold crossings

**⚠️ Risk Warning:**  
Penny stocks are highly volatile and risky. Always:
- Use proper position sizing
- Set stop losses
- Avoid stocks with pump-and-dump indicators
- Never invest more than you can afford to lose

---

## News Feed

**Location:** News → Feed

Real-time financial news with intelligent filtering.

### Features

**News Sources:**
- NewsAPI (10+ sources)
- Finnhub
- Alpha Vantage
- RSS feeds from major financial outlets

**Filtering Options:**
- By ticker symbol
- By sector (Technology, Healthcare, Finance, etc.)
- By category (Earnings, M&A, Regulatory, Economic)
- By sentiment (Positive, Neutral, Negative)
- By source credibility rating

**News Card Display:**
- Article title and summary
- Source and publication time
- Sentiment score with confidence
- Mentioned tickers
- Related stocks affected
- Social media buzz metrics

**Actions:**
- Click to read full article
- Save to reading list
- Create alert for similar news
- View impact analysis
- Share via link

### News Impact Analysis

**Location:** News → Impact Analysis

Analyzes how news affects stock prices over different timeframes.

**Timeframes Analyzed:**
- 1 hour after publication
- 4 hours after publication
- 1 day after publication
- 1 week after publication

**Metrics:**
- Price change percentage
- Volume change percentage
- Statistical significance
- Average impact by category

**Use Cases:**
- Identify which news types have strongest impact
- Determine optimal holding periods
- Find stocks most sensitive to news
- Validate news-based trading strategies


---

## Portfolio Management

**Location:** Portfolio → Dashboard

Track your holdings, watchlist, and portfolio performance.

### Portfolio Features

**Holdings Management:**
- Add positions (ticker, quantity, purchase price, date)
- Track current value and P&L
- View position sizes and allocation
- Calculate portfolio metrics (total return, Sharpe ratio)

**Watchlist:**
- Add/remove tickers
- Quick view of watchlist prices
- Alerts for watchlist stocks
- News feed for watchlist
- Batch analyze all watchlist stocks

**Performance Tracking:**
- Daily P&L
- Total return percentage
- Benchmark comparison (S&P 500)
- Equity curve chart
- Drawdown analysis

**Actions:**
- Buy/Sell positions (paper trading)
- Rebalance portfolio
- Export portfolio as CSV
- Generate performance report

### Portfolio Analytics

**Risk Metrics:**
- Portfolio beta
- Value at Risk (VaR)
- Maximum drawdown
- Volatility (standard deviation)
- Sharpe ratio, Sortino ratio

**Diversification:**
- Sector allocation pie chart
- Concentration risk analysis
- Correlation matrix
- Suggested rebalancing

---

## Alerts and Notifications

**Location:** Alerts → Configuration

Set up automated alerts for market conditions.

### Alert Types

**1. Price Alerts**
- Price crosses threshold (above/below)
- Price change percentage (gain/loss)
- New 52-week high/low
- Moving average crossovers

**Example:**
```
Alert me when AAPL > $180
Alert me when TSLA loses >5% in a day
```

**2. News Alerts**
- Breaking news mentioning watchlist stock
- Sentiment change >0.5 points
- Specific keywords in news (e.g., "acquisition")
- High-impact news for any stock

**Example:**
```
Alert me when any news mentions AAPL
Alert me when any stock has earnings announcement
```

**3. Technical Alerts**
- RSI oversold (<30) or overbought (>70)
- MACD crossover
- Bollinger Band breach
- Volume surge (>3x average)

**Example:**
```
Alert me when TSLA RSI < 30
Alert me when any watchlist stock has 3x volume
```


**4. Prediction Alerts**
- Daily prediction confidence >80%
- Prediction changes from previous day
- Strong Buy/Strong Sell signals

**Example:**
```
Alert me when prediction confidence > 80%
Alert me when any watchlist stock gets Strong Buy
```

### Delivery Channels

- **In-App Notifications:** Always enabled
- **Email:** Configure in Settings
- **Webhook:** For integration with Slack, Discord, etc.

### Alert Management

**Creating Alerts:**
1. Click "Create Alert"
2. Choose alert type
3. Select conditions and thresholds
4. Choose delivery channels
5. Save and activate

**Managing Alerts:**
- View all active alerts
- Enable/disable alerts
- Edit alert conditions
- Delete alerts
- View alert history

**Alert History:**
- See when alerts triggered
- Review market conditions at trigger time
- Track alert accuracy
- Export history as CSV

---

## Custom Screeners

**Location:** Screener → Create

Build custom stock screeners with 20+ criteria.

### Available Criteria

**Price & Volume:**
- Price range
- Market cap range
- Volume (absolute or ratio to average)
- Average volume
- Dollar volume

**Technical Indicators:**
- RSI (< or > value)
- MACD (bullish/bearish crossover)
- Moving averages (above/below)
- Bollinger Bands position
- ATR (volatility)

**Fundamental Metrics:**
- P/E ratio range
- EPS growth
- Revenue growth
- Profit margin
- Debt-to-equity ratio
- Return on equity (ROE)

**Sentiment:**
- News sentiment score
- Social media buzz
- Analyst ratings

**Other:**
- Sector
- Industry
- Exchange (NYSE, NASDAQ)
- Country


### Building a Screener

**Example: Value Stocks with Momentum**

1. Click "Create New Screener"
2. Add criteria:
   - P/E ratio < 15
   - ROE > 15%
   - RSI > 50 (showing momentum)
   - Volume > 500,000
   - Market cap > $1B
3. Combine with AND operator
4. Save as "Value with Momentum"
5. Run screener

**Results:**
- Table of matching stocks
- Sort by any column
- Click stock for detailed analysis
- Export results as CSV
- Save screener for recurring use

### Pre-Built Screeners

- **Growth Stocks:** High revenue/EPS growth
- **Value Stocks:** Low P/E, high dividend yield
- **Momentum:** RSI > 60, price above 20-day MA
- **Dividend Aristocrats:** 25+ years dividend growth
- **Small Cap Growth:** Market cap < $2B, growth > 20%
- **Breakout Candidates:** Near 52-week high, high volume

### Scheduled Screeners

Run screeners automatically:
- Daily before market open
- Weekly on Sundays
- Monthly on 1st of month

Receive results via email or in-app notification.

---

## Backtesting

**Location:** Backtest → Engine

Test trading strategies on historical data.

### Creating a Backtest

**1. Define Strategy**

Example strategies:
- **Moving Average Crossover:** Buy when 50-day MA crosses above 200-day MA
- **RSI Mean Reversion:** Buy when RSI < 30, sell when RSI > 70
- **Momentum:** Buy top 10 monthly gainers, hold for 30 days
- **News Sentiment:** Buy on positive news, sell on negative

**2. Configure Parameters**

```
Initial Capital: $100,000
Start Date: 2020-01-01
End Date: 2023-12-31
Commission: $0.00 per trade (or broker rate)
Slippage Model: Fixed (0.1%) or Volume-based
Position Sizing: Equal weight or Kelly Criterion
```

**3. Select Universe**

- Single stock
- Watchlist
- Sector (e.g., all Technology stocks)
- Screener results
- S&P 500

**4. Run Backtest**

Click "Run Backtest" - takes 30-60 seconds depending on data range.

### Results Analysis

**Performance Metrics:**
- Total Return: +45.2%
- Annual Return: 12.3%
- Max Drawdown: -18.5%
- Sharpe Ratio: 1.42
- Sortino Ratio: 1.85
- Win Rate: 58.3%
- Average Win: +3.2%
- Average Loss: -2.1%
- Total Trades: 156

**Charts:**
- Equity curve
- Drawdown chart
- Monthly returns heat map
- Trade distribution

**Trade Log:**
- Complete list of all trades
- Entry/exit dates and prices
- P&L per trade
- Holding period
- Export as CSV


### Walk-Forward Optimization

Test strategy robustness with walk-forward analysis:

1. Training period: 2 years
2. Testing period: 6 months
3. Step forward: 3 months
4. Automatically re-optimize parameters

**Benefits:**
- Prevents overfitting
- More realistic performance estimates
- Identifies parameter stability

---

## Paper Trading

**Location:** Trading → Paper Account

Practice trading with virtual money.

### Setting Up Paper Trading

1. Navigate to Trading → Paper Account
2. Set initial virtual capital (default: $100,000)
3. Start trading immediately

### Placing Orders

**Order Types:**
- **Market Order:** Execute at current market price
- **Limit Order:** Execute at specified price or better
- **Stop Loss:** Sell if price falls to specified level
- **Stop Limit:** Stop order becomes limit order when triggered

**Placing a Market Order:**
```
1. Click "Place Order"
2. Enter ticker: AAPL
3. Select "Market" order type
4. Enter quantity: 10 shares
5. Choose side: Buy
6. Review and confirm
```

**Placing a Limit Order:**
```
1. Click "Place Order"
2. Enter ticker: TSLA
3. Select "Limit" order type
4. Enter limit price: $250.00
5. Enter quantity: 5 shares
6. Choose side: Buy
7. Review and confirm
```

### Order Management

**View Orders:**
- Open orders (pending)
- Filled orders (executed)
- Cancelled orders
- Order history

**Actions:**
- Cancel open orders
- Modify limit orders
- View execution details

### Performance Tracking

**Account Summary:**
- Current cash balance
- Total equity (cash + positions)
- Total P&L ($ and %)
- Day P&L
- Buying power

**Position Details:**
- Holdings by ticker
- Quantity and average cost
- Current value and P&L
- Percentage of portfolio

**Trade History:**
- All executed trades
- Entry/exit prices
- P&L per trade
- Cumulative P&L
- Export as CSV

**Performance Charts:**
- Equity curve
- Daily P&L
- Win/loss distribution
- Holding period analysis


### Paper Trading Best Practices

1. **Treat it like real money** - Take it seriously to build good habits
2. **Follow your strategy** - Don't deviate from your plan
3. **Keep a trading journal** - Document reasons for each trade
4. **Track emotions** - Note how you feel during wins/losses
5. **Review performance** - Weekly review of what worked and what didn't
6. **Start small** - Begin with small positions, increase as you improve
7. **Set stop losses** - Practice risk management
8. **Paper trade for 3-6 months** before using real money

---

## Tips and Best Practices

### Using the Daily Brief

**Morning Routine:**
1. Check Daily Market Brief at 8:00 AM ET
2. Review top movers and breaking news
3. Check predictions for watchlist stocks
4. Review alerts triggered overnight
5. Plan trading day based on insights

**During Market Hours:**
1. Monitor real-time top movers (refreshes every 5 minutes)
2. Check news feed for breaking developments
3. Watch for alert notifications
4. Review penny stock dashboard for opportunities

**Evening Review:**
1. Check closed positions and P&L
2. Review prediction accuracy
3. Read market summary
4. Plan for next trading day

### Interpreting ML Predictions

**Confidence Scores:**
- **80-100%:** High confidence - Strong signal
- **60-80%:** Moderate confidence - Good signal
- **40-60%:** Low confidence - Weak signal, use caution
- **<40%:** Very low confidence - Avoid or wait for better signal

**Combining Signals:**

Best results come from combining multiple signals:
- ML prediction + Positive news sentiment = Stronger buy signal
- Technical breakout + High prediction confidence = Trade opportunity
- Fundamental strength + Positive prediction = Long-term hold candidate

**Cautions:**
- No prediction is 100% accurate
- Past accuracy doesn't guarantee future results
- Use predictions as one input among many
- Always use stop losses and position sizing


### Risk Management

**Position Sizing:**
- Never risk more than 1-2% of portfolio per trade
- Use smaller positions for higher-risk stocks
- Diversify across sectors and market caps

**Stop Losses:**
- Always use stop losses
- Common stops: 5-10% below entry for swings, 2-3% for day trades
- Adjust stops based on volatility (ATR)

**Diversification:**
- Hold 15-20 positions for adequate diversification
- Limit single position to 10% of portfolio
- Spread across multiple sectors

**Risk Metrics to Monitor:**
- Portfolio beta (market sensitivity)
- VaR (Value at Risk)
- Maximum drawdown
- Correlation between positions

### News Analysis Tips

**Sentiment Interpretation:**
- **+0.5 to +1.0:** Very positive - Bullish signal
- **+0.2 to +0.5:** Positive - Mildly bullish
- **-0.2 to +0.2:** Neutral - No clear signal
- **-0.5 to -0.2:** Negative - Mildly bearish
- **-1.0 to -0.5:** Very negative - Bearish signal

**Source Credibility:**
- Prioritize news from major outlets (WSJ, Bloomberg, Reuters)
- Be cautious with unknown sources
- Cross-reference important news across multiple sources
- Check publication time - old news may already be priced in

**News Impact Timing:**
- Earnings news: Strongest impact in first 4 hours
- M&A news: Impact over 1-2 days
- Regulatory news: Longer-term impact (weeks)
- Economic news: Immediate market-wide impact

### Penny Stock Trading Cautions

**Red Flags (Avoid):**
- No news or catalyst for sudden gain
- High pump-and-dump suspicion score
- Extremely low volume (<10,000 shares/day)
- Wide bid-ask spreads (>10%)
- No fundamentals (earnings, revenue)

**Green Flags (Potentially legitimate):**
- Clear catalyst (FDA approval, contract win, earnings beat)
- Increasing volume over multiple days
- Institutional interest
- Positive news from credible sources
- Company has real products/revenue

**Trading Rules:**
- Use limit orders only (never market orders)
- Start with very small positions
- Take profits quickly (20-30% gains)
- Cut losses fast (5-10% stops)
- Never hold overnight without good reason

---

## Keyboard Shortcuts

### Web Interface

| Shortcut | Action |
|----------|--------|
| `Ctrl + K` | Open ticker search |
| `Ctrl + /` | Focus on search bar |
| `Ctrl + R` | Refresh data |
| `Ctrl + D` | Add to watchlist |
| `Ctrl + N` | Create new alert |
| `Ctrl + S` | Save current view |
| `Esc` | Close modals/dialogs |

---

## Frequently Asked Questions

**Q: How often does data update?**  
A: Top movers every 5 minutes, news every 10 minutes, penny stocks every 2 minutes during market hours.

**Q: Can I use this for day trading?**  
A: The platform provides tools for day trading, but focus on swing trading for best results with the prediction engine.

**Q: How accurate are the predictions?**  
A: Historical accuracy is typically 60-70% for 30-day forecasts. Check the "Prediction Performance" page for current accuracy.

**Q: Can I export my data?**  
A: Yes, all data can be exported as CSV, and reports can be exported as PDF.

**Q: Is my data secure?**  
A: Yes, the platform uses industry-standard security practices. Portfolio data is stored locally in your database instance.

**Q: Can I use my own API keys?**  
A: Yes, configure API keys in the `.env` file.

**Q: Does it work with international stocks?**  
A: Currently optimized for US markets (NYSE, NASDAQ). International support coming in future release.

---

## Getting Help

- **Documentation:** Full docs at `/docs`
- **GitHub Issues:** Report bugs or request features
- **Community:** Join discussions on GitHub Discussions
- **Email:** support@stockiq.example.com

---

## Next Steps

Now that you're familiar with the platform:

1. **Explore the Daily Brief** - Your morning market intelligence
2. **Set up your watchlist** - Track your favorite stocks
3. **Create alerts** - Never miss important events
4. **Try paper trading** - Practice before using real money
5. **Build a screener** - Find opportunities matching your criteria
6. **Backtest a strategy** - Validate your trading ideas

*For technical details, see the [API Reference](api-reference.md). For development, see the [Developer Guide](developer-guide.md).*
