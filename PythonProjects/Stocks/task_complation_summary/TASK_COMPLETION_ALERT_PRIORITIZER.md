# Task Completion: Alert Prioritizer

**Status:** Completed ✅  
**Date:** 2026-06-19

---

## Task Title

`Implement alert prioritization in stockiq/news/alerts/prioritizer.py`

---

## Files Created or Modified

| File | Action | Description |
|------|--------|-------------|
| `stockiq/news/alerts/prioritizer.py` | Verified/existing | Full implementation of `calculate_priority` and `group_related_alerts` |
| `stockiq/news/alerts/__init__.py` | Verified/existing | Exports `AlertGroup`, `calculate_priority`, `group_related_alerts` |
| `tests/test_alert_prioritizer.py` | Created | 35-test suite covering all functionality and property-based tests |

---

## What Was Implemented

### `calculate_priority(alert: NewsAlert) -> int`

Returns an integer urgency score composed of three parts:

1. **Base score by alert type** (enforces required ordering):
   - `BREAKING_NEWS` → 100
   - `EARNINGS` → 80
   - `M&A` → 60
   - `REGULATORY` → 40
   - `SENTIMENT_CHANGE` → 30
   - `GENERAL` → 20

2. **Sentiment magnitude bonus** (0–10): proportional to `|sentiment_score|`, capped at 1.0. A score of ±1.0 contributes the full +10.

3. **Predicted impact bonus** (0–10): proportional to `|predicted_impact|`, capped at 1.0. Only applied when `predicted_impact` is not `None`.

Maximum possible score: 120 (breaking news + max sentiment + max impact).

### `group_related_alerts(alerts: List[NewsAlert]) -> List[AlertGroup]`

Groups alerts by ticker within a 1-hour sliding window to prevent notification spam:

1. Sorts alerts chronologically by `triggered_at`.
2. For each alert, finds an existing open group for the same ticker where the window start (earliest alert in group) is within 60 minutes of the current alert.
3. If no matching group exists, opens a new one.
4. Returns all groups sorted by `highest_priority` descending so callers deliver the most urgent notifications first.

### `AlertGroup` dataclass

- `ticker`: str — the ticker all alerts share
- `alerts`: List[NewsAlert] — chronologically ordered
- `highest_priority`: int — pre-computed max priority across all alerts in group
- `count` property: number of alerts in group
- `add(alert, priority)` method: appends alert and updates `highest_priority`

---

## Tests

**File:** `tests/test_alert_prioritizer.py`  
**Result:** 35 / 35 passed ✅

| Test Class | Tests | What it covers |
|---|---|---|
| `TestCalculatePriorityBaseScores` | 7 | Ordering: BREAKING > EARNINGS > MA > REGULATORY > GENERAL, exact base values |
| `TestCalculatePrioritySentimentBonus` | 5 | Zero/half/max sentiment, negative magnitude, capping above 1.0 |
| `TestCalculatePriorityImpactBonus` | 5 | None/zero/half/max/negative impact, stacking both bonuses |
| `TestGroupRelatedAlertsBasic` | 7 | Empty input, single alert, same-window grouping, different tickers, boundary at exactly 1h, case-insensitive ticker |
| `TestGroupRelatedAlertsPriorityOrdering` | 2 | Groups sorted descending, `highest_priority` reflects max alert in group |
| `TestGroupRelatedAlertsSpamPrevention` | 2 | 10 alerts same ticker → 1 group; 2 separate time windows → 2 groups |
| `TestAlertGroupHelpers` | 3 | `count`, `add`, initial `highest_priority` |
| `TestPriorityProperties` (Hypothesis) | 4 | Priority always ≥ 0, all types positive, group count conservation, groups sorted descending |

---

## Requirements Satisfied

| Requirement | Description |
|---|---|
| 5.7 | Include sentiment score and predicted price impact in alert evaluation |
| 5.8 | Alert sensitivity considered via configurable threshold (base scores + bonuses) |
| 5.10 | Group related alerts to avoid notification spam (1-hour window per ticker) |
| 5.12 | Prioritize alerts by predicted market impact when multiple high-impact items occur |

---

## Notes

- The prioritizer is purely in-memory and stateless — no database or Redis dependency required, consistent with the graceful degradation design principle.
- `group_related_alerts` uses a stable window anchored to the **earliest** alert in a group (not a rolling window), so groups have a fixed 1-hour span.
- The `__init__.py` already exports all public symbols; no changes needed there.
- Next ready task unlocked by this completion: **`Implement penny stock alert system in stockiq/news/alerts/penny_alerts.py`**
