# Live Paper Auto-Trader — Deployment Complete ✅

## Summary

The live paper auto-trader is now **deployed and running**. Users can create bots that automatically trade paper accounts using real-time market data.

---

## Architecture

### Backend Components

**1. Database Tables (Migration 005)**
- `autotrade_bots` — Bot configuration (name, ticker, strategy, risk params, stats)
- `autotrade_logs` — Execution audit trail (signal, action, order ID, details)

**2. Service Layer** (`backend/autotrade/`)
- `models.py` — SQLAlchemy ORM models with full stats tracking
- `service.py` — BotService for CRUD + execution state updates
- `executor.py` — BotExecutor runs strategy evaluation + order placement
- `router.py` — REST API for bot management + logs

**3. Execution Engine**
- **Celery Beat Task** (`stockiq/infrastructure/tasks.py`)
  - `run_autotrade_bots()` — Runs every 5 minutes during market hours
  - Schedule: `crontab(minute='*/5', hour='9-16', day_of_week='mon-fri')`
  - Fetches all enabled bots, runs each via `BotExecutor.run_bot(bot_id)`

**4. Execution Flow** (per bot, every 5 minutes)
1. Fetch 60 days of daily OHLCV bars from yfinance
2. Build strategy + RiskManager from bot config
3. Check if user has an open position in the ticker
4. Evaluate strategy → BUY / SELL / HOLD signal with confidence
5. Log signal to `autotrade_logs`
6. **If BUY + no position:**
   - Run signal through RiskManager.evaluate_entry()
   - If approved: place paper order via TradingService
   - If blocked: log "risk_blocked" with reason
7. **If SELL + has position:**
   - Place paper sell order, close position
   - Update bot stats (total_trades, winning_trades, total_pnl)
8. Update bot.last_run_at, last_signal, last_error

### Frontend Components

**1. AutoTrade Page** (`frontend/src/pages/AutoTradePage.tsx`)
- **Bot List** — Cards showing name, ticker, strategy, enabled state, stats
- **Create/Edit Modal** — Form with strategy picker + 5 risk sliders
- **Logs Modal** — Live execution history (signal, action, order ID)
- **Auto-refresh** — Bots refetch every 30s, logs every 10s

**2. API Client** (`frontend/src/api/autotrade.ts`)
- `createBot()`, `listBots()`, `updateBot()`, `deleteBot()`, `getBotLogs()`

**3. Navigation**
- Route: `/autotrade`
- Sidebar: "Auto-Trade" with Bot icon

---

## REST API Endpoints

All require JWT authentication.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/autotrade/strategies` | List available strategies |
| POST | `/autotrade/backtest` | Run historical backtest |
| POST | `/autotrade/bots` | Create a new bot |
| GET | `/autotrade/bots` | List user's bots |
| GET | `/autotrade/bots/{id}` | Get bot details |
| PATCH | `/autotrade/bots/{id}` | Update bot config or toggle enabled |
| DELETE | `/autotrade/bots/{id}` | Delete bot |
| GET | `/autotrade/bots/{id}/logs` | Get execution logs (limit=100) |

---

## Bot Configuration

Each bot tracks:

**Strategy** (one of):
- `momentum` — Buy strong uptrends, sell on weakness
- `mean_reversion` — Buy oversold, sell overbought
- `ma_crossover` — SMA crossover signals

**Risk Parameters** (configurable via UI sliders):
- Position Size: 1–100% of equity
- Stop Loss: 0.5–20%
- Take Profit: 0.5–50%
- Daily Loss Limit: 1–50%
- Min Confidence: 0–100%
- Max Positions: 1–10
- Max Trades/Day: 1–50

**Tracked Stats**:
- Total Trades
- Winning Trades
- Total P&L (cumulative realized)
- Win Rate (auto-calculated)

---

## Celery Beat Schedule

The auto-trader runs **every 5 minutes** during market hours:

```python
"run-autotrade-bots": {
    "task": "stockiq.infrastructure.tasks.run_autotrade_bots",
    "schedule": crontab(minute="*/5", hour="9-16", day_of_week="mon-fri"),
    "options": {"queue": "celery", "priority": 8},
}
```

**Market Hours:** 9:30 AM – 4:00 PM ET, Monday–Friday  
**Schedule Coverage:** 9:00 AM – 4:59 PM (every :00, :05, :10, ..., :55)

---

## Safety Features

1. **Paper Trading Only** — Never touches real money
2. **Risk Manager Gates** — All signals pass through risk checks
3. **Error Isolation** — Individual bot failures never crash the task
4. **Audit Trail** — Every execution logged to `autotrade_logs`
5. **User Control** — Enable/disable bots instantly via UI toggle

---

## Deployment Status

✅ Database migration applied (005)  
✅ Backend API deployed and running  
✅ Frontend built and serving  
✅ Celery beat scheduling active  
✅ Auto-trader task registered and firing every 5 minutes  

**Access:**
- Frontend: http://localhost:3000/autotrade
- Backend API: http://localhost:8000/api/v1/autotrade

---

## Testing the Auto-Trader

### 1. Create a Bot

```bash
# Login and get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Create a bot
curl -X POST http://localhost:8000/api/v1/autotrade/bots \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My First Bot",
    "ticker": "AAPL",
    "strategy": "momentum",
    "enabled": true,
    "risk": {
      "position_size_pct": 0.10,
      "stop_loss_pct": 0.02,
      "take_profit_pct": 0.04,
      "daily_loss_limit_pct": 0.03,
      "max_positions": 5,
      "max_trades_per_day": 10,
      "min_confidence": 55
    }
  }'
```

### 2. Monitor Execution

**Via UI:**
1. Navigate to http://localhost:3000/autotrade
2. View bot card (shows last run time, last signal, stats)
3. Click "View Logs" to see execution history

**Via API:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/v1/autotrade/bots/{BOT_ID}/logs
```

**Via Celery Logs:**
```bash
docker compose logs -f celery-worker | grep "Bot.*run"
```

### 3. Expected Behavior

- Bot runs every 5 minutes (if market is open)
- Each run:
  - Fetches 60 days of bars from yfinance
  - Evaluates strategy
  - Logs signal (BUY/SELL/HOLD) to `autotrade_logs`
  - If BUY + no position: attempts to place order via risk manager
  - If SELL + has position: closes position
  - Updates `last_run_at`, `last_signal` in DB

---

## Next Steps

1. **Add Strategy Parameters** — Allow users to tune indicator settings (e.g., SMA periods)
2. **Add Position Monitoring** — Check open positions for stop-loss / take-profit triggers
3. **Add Performance Analytics** — Sharpe ratio, max drawdown, win/loss distribution charts
4. **Add Email/SMS Alerts** — Notify users when bots place orders or hit stop-losses
5. **Add Multi-Ticker Bots** — Let one bot manage a basket of tickers

---

## Technical Notes

- **Data Source:** yfinance (60-day daily bars)
- **Signal Evaluation:** Runs in Celery worker (synchronous)
- **Order Placement:** Paper orders via TradingService (in-memory positions)
- **Risk Checks:** RiskManager.evaluate_entry() before every BUY
- **Error Handling:** All exceptions caught and logged to `bot.last_error`

---

## File Manifest

**Backend:**
- `backend/autotrade/models.py` — AutoTradeBotDB, AutoTradeLogDB
- `backend/autotrade/service.py` — BotService CRUD + stats
- `backend/autotrade/executor.py` — BotExecutor execution engine
- `backend/autotrade/router.py` — REST endpoints
- `backend/autotrade/schemas.py` — Pydantic models
- `backend/migrations/versions/005_create_autotrade_tables.py` — DB migration
- `stockiq/infrastructure/tasks.py` — Celery task + beat schedule

**Frontend:**
- `frontend/src/pages/AutoTradePage.tsx` — Main UI
- `frontend/src/api/autotrade.ts` — API client
- `frontend/src/App.tsx` — Route registration
- `frontend/src/components/layout/Sidebar.tsx` — Nav link

---

**Deployment Complete** — The live paper auto-trader is ready for use! 🚀
