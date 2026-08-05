# Requirements Document

## Introduction

StockIQ React UI Upgrade migrates every page from the existing Streamlit application into the production React + TypeScript frontend and enriches the already-built pages with premium UI polish. The result is a single-page application that covers the complete StockIQ feature set: Daily Market Brief, Penny Stocks Dashboard, News Feed, Predictions, Alerts, Watchlist, Settings, and all currently-shipped pages (Dashboard, Portfolio, Trading, Stock Detail). Shared UI primitives — glassmorphism cards, accordion expand/fold bars, sentiment badges, and animated progress bars — are extracted into a reusable component library consumed across the entire app.

## Glossary

- **React_App**: The React 18 + TypeScript + Vite frontend application located at `frontend/`.
- **AppShell**: The top-level layout component (`AppShell.tsx`) that renders the collapsible Sidebar and the mobile bottom navigation bar.
- **Sidebar**: The collapsible left-navigation panel that lists all application routes.
- **Page**: A top-level routed view rendered inside AppShell (e.g. `DailyBriefPage`, `PennyStocksPage`).
- **GlassCard**: The shared premium card component with glassmorphism background, gradient border, and hover scale effect.
- **AccordionRow**: The shared expand/fold bar component used to reveal per-ticker detail panels.
- **SentimentBadge**: A coloured pill component that encodes news sentiment as Positive (green), Neutral (yellow), or Negative (red).
- **ConfidenceBar**: An animated horizontal progress bar that displays a percentage value with an aria `progressbar` role.
- **TopMoverCard**: A card inside the Top Movers list that summarises ticker price change and volume.
- **MomentumTable**: The sortable data table on the Penny Stocks page listing up to 20 penny stocks by momentum score.
- **DailyBriefPage**: The new React page mirroring the Streamlit "Daily Market Brief" dashboard, served at route `/market`.
- **PennyStocksPage**: The new React page mirroring the Streamlit "Penny Stocks" dashboard, served at route `/penny-stocks`.
- **NewsFeedPage**: The new React page mirroring the Streamlit "News Feed", served at route `/news`.
- **PredictionsPage**: The new React page showing ML ensemble predictions, served at route `/predictions`.
- **AlertsPage**: The new React page showing real-time market alerts, served at route `/alerts`.
- **SettingsPage**: The new React page for application configuration, served at route `/settings`.
- **StockSearchBox**: A controlled input that resolves a ticker symbol and displays inline trend, news, and prediction.
- **Backend_API**: The existing FastAPI application at `backend/` with base path `/api/v1/`.
- **TanStack_Query**: The `@tanstack/react-query` v5 data-fetching library used for all API calls.
- **Framer_Motion**: The animation library used for page transitions and component entrance effects.
- **Recharts**: The charting library already integrated in the React_App.
- **MomentumScore**: A numeric score (0–100) ranking a penny stock's price momentum.
- **SentimentScore**: A decimal in [-1, 1] representing NLP-derived article sentiment.
- **ConfidenceScore**: A decimal in [0, 1] representing the AI model's prediction certainty.

---

## Requirements

### Requirement 1: Shared UI Component Library

**User Story:** As a developer, I want a shared set of premium UI primitives, so that every page looks and behaves consistently without copy-pasting styles.

#### Acceptance Criteria

1. THE React_App SHALL export a `GlassCard` component that applies a semi-transparent dark background (`bg-[#111827]/80`), a gradient border, and a `backdrop-blur` filter.
2. WHEN a user hovers over a `GlassCard`, THE React_App SHALL animate the component to a scale of 1.02 via Framer_Motion over no more than 200 milliseconds.
3. THE React_App SHALL export an `AccordionRow` component that accepts `header` and `children` props, renders the header in a clickable bar in a collapsed state by default, and toggles the children panel with a Framer_Motion height animation.
4. WHEN `AccordionRow` is toggled, THE React_App SHALL animate the expand or collapse over no more than 300 milliseconds.
5. THE React_App SHALL export a `SentimentBadge` component that accepts a `score` prop of type `number` and renders a green badge for `score > 0.15`, a yellow badge for `score >= -0.15 && score <= 0.15`, and a red badge for `score < -0.15`.
6. THE React_App SHALL export a `ConfidenceBar` component that accepts `value` (0–100) and `color` (a valid CSS color string) props and renders an animated horizontal bar with `role="progressbar"`, `aria-valuenow` set to `value`, `aria-valuemin={0}`, and `aria-valuemax={100}`.
7. WHEN `ConfidenceBar` mounts, THE React_App SHALL animate the bar width from 0 to `value` over no more than 500 milliseconds using Framer_Motion.
8. THE React_App SHALL export a `PageTransition` wrapper that uses `AnimatePresence` and a Framer_Motion `motion.div` with `initial={{ opacity: 0, y: 8 }}`, `animate={{ opacity: 1, y: 0 }}`, `exit={{ opacity: 0, y: -8 }}`, and a transition duration of no more than 300 milliseconds.
9. THE React_App SHALL export a `SkeletonPulse` component that renders a single pulsing `animate-pulse` block with `role="status"` and `aria-label="Loading"`, accepting `className` for size customisation.
10. WHERE the user is on a mobile viewport (< 768 px), THE React_App SHALL render all multi-column grid layouts as single-column stacks without horizontal scrolling.

---

### Requirement 2: Navigation — Sidebar and Mobile Nav Upgrade

**User Story:** As a trader, I want a sidebar that includes all application pages, so that I can switch between any section in one click.

#### Acceptance Criteria

1. THE Sidebar SHALL render navigation links for Dashboard, Portfolio, Watchlist, Trading, Stock Search, Daily Market Brief, Penny Stocks, News Feed, Predictions, Alerts, and Settings.
2. WHEN the Sidebar is collapsed, THE Sidebar SHALL display only icon glyphs with `title` tooltips and no text labels, and the sidebar width SHALL be 48 px.
3. WHEN the Sidebar is expanded, THE Sidebar SHALL display both icon glyphs and text labels; text labels longer than 20 characters SHALL be truncated with an ellipsis, and each nav item SHALL have a minimum hit area of 48 px tall.
4. THE Sidebar SHALL visually highlight the active route using the `bg-primary/10 text-primary` classes on the active `NavLink`.
5. THE React_App SHALL update the mobile bottom navigation bar to include icons for Dashboard, Market, Penny Stocks, News, and Alerts (five tabs maximum).
6. WHEN a Sidebar nav item is clicked, THE React_App SHALL perform client-side navigation to the corresponding route without a full-page reload.
7. THE AppShell SHALL render a top header bar containing the page title derived from the current route, a global stock search input accepting 1–10 uppercase alphanumeric characters, and a notification bell icon.
8. WHEN the notification bell is clicked and the unread alert count is between 1 and 99 inclusive, THE AppShell SHALL display that count as a badge overlay on the bell icon.
9. WHEN the unread alert count exceeds 99, THE AppShell SHALL display "99+" as the badge overlay text on the bell icon.
10. WHEN the unread alert count is 0, THE AppShell SHALL display no badge overlay on the bell icon.

---

### Requirement 3: Daily Market Brief Page

**User Story:** As a trader, I want a Daily Market Brief landing page, so that I can see top movers, key news, and predictions in one view the moment I open the app.

#### Acceptance Criteria

1. THE DailyBriefPage SHALL be served at route `/market` and SHALL be the default redirect from `/` when the user is authenticated.
2. THE DailyBriefPage SHALL render a three-column layout on viewports >= 1024 px with the left column showing Top Movers, the centre column showing Market News, and the right column showing Daily Predictions.
3. THE DailyBriefPage SHALL display the top 10 gainers and top 10 losers in side-by-side sub-columns within the Top Movers left column.
4. WHEN Top Movers data is loading, THE DailyBriefPage SHALL display `SkeletonPulse` placeholders for each of the 20 mover rows.
5. THE DailyBriefPage SHALL render each gainer or loser entry as a `TopMoverCard` showing ticker symbol (1–10 uppercase alphanumeric characters), percentage change coloured green when `price_change_pct` is positive and red when negative, current price, and volume.
6. WHERE a ticker has volume exceeding 1.5× its average volume, THE DailyBriefPage SHALL display a flame icon (🔥) on the `TopMoverCard`.
7. THE DailyBriefPage SHALL render each `TopMoverCard` as an `AccordionRow` that, when expanded, shows the ticker's news explanation and AI prediction detail inside a `GlassCard`.
8. WHEN an `AccordionRow` inside Top Movers is expanded, THE DailyBriefPage SHALL fetch news for that specific ticker and display up to 3 articles with `SentimentBadge` inline.
9. WHEN an `AccordionRow` inside Top Movers is expanded, THE DailyBriefPage SHALL display the AI prediction for that ticker including signal category, a `ConfidenceBar`, and expected return percentage.
10. THE DailyBriefPage SHALL display up to 5 market news stories in the centre column, each with a `SentimentBadge`, source, relative timestamp (e.g., "2 minutes ago"), and a summary of no more than 300 characters.
11. WHEN an article is marked `is_breaking: true`, THE DailyBriefPage SHALL prepend a red "BREAKING" pill to that article's title.
12. THE DailyBriefPage SHALL display up to 8 prediction rows in the right column, each showing ticker, signal-category badge, `ConfidenceBar`, and expected return.
13. THE DailyBriefPage SHALL render a `StockSearchBox` above the three columns that, on submission, resolves the ticker via `GET /api/v1/market/quote/{ticker}` and displays trend arrow, price, volume, news, and prediction.
14. WHEN the `StockSearchBox` receives an unrecognised ticker (HTTP 404), THE DailyBriefPage SHALL display an inline error message "Symbol not found" without navigating away.
15. WHEN the `StockSearchBox` fetch fails with a non-404 error, THE DailyBriefPage SHALL display an inline error message "Unable to load data — please try again" and preserve the current search input.
16. THE DailyBriefPage SHALL refetch Top Movers data at a staleTime of 300 seconds using TanStack_Query.
17. WHEN the DailyBriefPage mounts, THE React_App SHALL apply the `PageTransition` entrance animation.
18. IF the `GET /api/v1/market/movers` request fails, THEN THE DailyBriefPage SHALL display an inline error message within the Top Movers section and a retry button.

---

### Requirement 4: New Backend API Endpoints for Daily Brief

**User Story:** As a developer, I want dedicated API endpoints for the Daily Market Brief data, so that the React frontend can retrieve structured market data efficiently.

#### Acceptance Criteria

1. THE Backend_API SHALL expose `GET /api/v1/market/movers` that returns `{ gainers: TopMover[], losers: TopMover[] }` where each `TopMover` contains `ticker`, `name`, `price_change_pct`, `current_price`, `volume`, `avg_volume`, `sector`, and `has_unusual_volume`.
2. THE Backend_API SHALL expose `GET /api/v1/market/news` with optional query param `limit` (default 5, max 20) that returns an array of news items each containing `title`, `source`, `published_at`, `sentiment_score`, `category`, `is_breaking`, `summary`, `tickers`, and `url`.
3. THE Backend_API SHALL expose `GET /api/v1/market/news/{ticker}` with optional `limit` (default 3, max 20) that returns news articles filtered to the given ticker.
4. THE Backend_API SHALL expose `GET /api/v1/market/predictions` with optional `tickers` query param (comma-separated, max 50 tickers per request) that returns an array of prediction objects each containing `ticker`, `category`, `confidence`, `expected_return`, `lower_bound`, `upper_bound`, and `is_low_confidence`.
5. WHEN any `/api/v1/market/*` endpoint is called without a valid JWT Bearer token, THE Backend_API SHALL return HTTP 401.
6. IF a ticker supplied to `GET /api/v1/market/news/{ticker}` does not match any known symbol, THEN THE Backend_API SHALL return HTTP 404 with a descriptive message.
7. IF a `limit` param is supplied outside its valid range, THEN THE Backend_API SHALL return HTTP 422 with a descriptive validation error.
8. IF the upstream market data source is unavailable, THEN THE Backend_API SHALL return HTTP 503 with a descriptive message.

---

### Requirement 5: Penny Stocks Dashboard Page

**User Story:** As a momentum trader, I want a Penny Stocks Dashboard, so that I can identify high-momentum sub-$5 stocks with risk metrics and sector context.

#### Acceptance Criteria

1. THE PennyStocksPage SHALL be served at route `/penny-stocks`.
2. THE PennyStocksPage SHALL render a `MomentumTable` showing up to 20 penny stocks with columns: rank, ticker, price, percentage change, volume ratio, momentum score, and risk level badge.
3. THE MomentumTable SHALL be sorted by `MomentumScore` descending on first render; subsequent clicks on the `MomentumScore` column header SHALL toggle between descending and ascending order.
4. WHEN the user clicks a column header of the `MomentumTable`, THE PennyStocksPage SHALL re-sort the table by that column, toggling between ascending and descending order.
5. THE PennyStocksPage SHALL render a price-history chart with tab selector for 1D, 5D, and 30D views defaulting to the highest-ranked ticker in the `MomentumTable` on first render.
6. WHEN the user selects a timeframe tab (1D / 5D / 30D), THE PennyStocksPage SHALL reload chart data for the selected period without remounting the chart component, displaying a loading indicator within the chart area during the fetch.
7. THE PennyStocksPage SHALL render a sector distribution donut chart showing the count of trending penny stocks per sector.
8. THE PennyStocksPage SHALL render risk metric cards for the top 5 penny stocks by `momentum_score`, showing liquidity risk, volatility risk, bid-ask spread percentage, and insider activity.
9. WHERE a penny stock has a `suspicion_score > 0.65`, THE PennyStocksPage SHALL display a "Pump & Dump Risk" warning badge on that stock's risk card.
10. THE PennyStocksPage SHALL poll `GET /api/v1/market/penny-stocks` every 120 seconds using TanStack_Query `refetchInterval`.
11. THE Backend_API SHALL expose `GET /api/v1/market/penny-stocks` that returns an array of penny stock objects including `ticker`, `price`, `price_change_pct`, `volume`, `avg_volume`, `volume_ratio`, `momentum_score`, `risk_level`, `sector`, `catalyst`, `suspicion_score`, `recommendation`, `insider_net`, `insider_buys`, and `insider_sells`.
12. IF the `GET /api/v1/market/penny-stocks` request fails, THEN THE PennyStocksPage SHALL retain the last successfully fetched data and display a non-blocking banner indicating data may be stale.

---

### Requirement 6: News Feed Page

**User Story:** As a trader, I want a dedicated News Feed page, so that I can read all market news with NLP sentiment scoring and filter by ticker or sentiment.

#### Acceptance Criteria

1. THE NewsFeedPage SHALL be served at route `/news`.
2. THE NewsFeedPage SHALL render a paginated list of news articles, loading 20 articles per page via `GET /api/v1/market/news?limit=20&offset={offset}`.
3. EACH news article card SHALL display title, `SentimentBadge`, source name, relative timestamp (e.g., "2 minutes ago", "3 hours ago"), category tag, relevant tickers as clickable chips, and a collapsible summary paragraph.
4. WHEN a ticker chip on a news article is clicked, THE NewsFeedPage SHALL navigate to `/stock/{ticker}`.
5. THE NewsFeedPage SHALL render a filter toolbar with a ticker search input accepting 1–5 uppercase alphabetic characters, a sentiment filter (All / Positive / Neutral / Negative), and a category filter (All / Earnings / Economic / M&A / Regulatory).
6. WHEN any filter is changed, THE NewsFeedPage SHALL reset the offset to 0 and re-fetch articles with the updated filter parameters.
7. WHEN a user clicks "Load more" or the viewport scrolls to within 200px of the bottom of the list, THE NewsFeedPage SHALL append the next page of 20 articles without reloading the page.
8. THE NewsFeedPage SHALL display a "Breaking News" section at the top pinning up to 5 articles where `is_breaking` is true, ordered by timestamp descending.
9. WHEN there are no articles matching the active filters, THE NewsFeedPage SHALL display an empty-state message "No news matching your filters."
10. IF the `GET /api/v1/market/news` request fails, THEN THE NewsFeedPage SHALL display an error message and a retry action.

---

### Requirement 7: Predictions Page

**User Story:** As an investor, I want a Predictions page, so that I can review all AI ensemble predictions across my watchlist stocks with confidence scores.

#### Acceptance Criteria

1. THE PredictionsPage SHALL be served at route `/predictions`.
2. THE PredictionsPage SHALL fetch predictions for all watchlist tickers via `GET /api/v1/market/predictions?tickers={watchlist}` on mount; IF the watchlist is empty, THEN THE PredictionsPage SHALL display an empty-state message "Add stocks to your watchlist to see predictions."
3. THE PredictionsPage SHALL render each prediction as a `GlassCard` containing ticker badge, signal-category badge (Strong Buy / Buy / Hold / Sell / Strong Sell), `ConfidenceBar`, expected return, and predicted range (lower_bound to upper_bound).
4. WHEN `is_low_confidence` is true for a prediction, THE PredictionsPage SHALL overlay a yellow "Low Confidence" warning chip on that `GlassCard`.
5. THE PredictionsPage SHALL support filtering predictions by category: "all" shows all signals; "bullish" shows Strong Buy and Buy; "bearish" shows Sell and Strong Sell; "neutral" shows Hold.
6. WHEN predictions are loading, THE PredictionsPage SHALL show `SkeletonPulse` placeholders for up to 8 prediction cards.
7. WHEN no trained model is available and the API returns sample data, THE PredictionsPage SHALL display a banner "Showing sample predictions — connect ML model for live forecasts."
8. THE PredictionsPage SHALL render a "Retrain Model" button visible only to users with the `admin` role; WHEN clicked, THE PredictionsPage SHALL call `POST /api/v1/market/predictions/train` and display a success message on HTTP 200 or an error message on failure.
9. IF the `GET /api/v1/market/predictions` request fails, THEN THE PredictionsPage SHALL display an error message and a retry action.

---

### Requirement 8: Alerts Page

**User Story:** As a trader, I want an Alerts page, so that I can see and acknowledge real-time market alerts without missing critical events.

#### Acceptance Criteria

1. THE AlertsPage SHALL be served at route `/alerts`.
2. THE AlertsPage SHALL fetch active alerts via `GET /api/v1/market/alerts` on mount and re-fetch every 30 seconds.
3. THE AlertsPage SHALL render each alert as a `GlassCard` with fields: ticker, alert type, message, severity level (info / warning / critical), and timestamp.
4. WHEN an alert has severity `critical`, THE AlertsPage SHALL render the card with a red left border accent and a pulsing dot indicator.
5. WHEN the user clicks "Dismiss" on an alert and the `DELETE /api/v1/market/alerts/{id}` call returns HTTP 204, THE AlertsPage SHALL remove the card from the list with a Framer_Motion exit animation; IF the call fails, THEN THE AlertsPage SHALL retain the card and display an error message.
6. WHEN a new alert arrives on re-fetch that was not in the previous response, THE AlertsPage SHALL animate the new card into the list from the top using Framer_Motion `AnimatePresence`.
7. WHEN the user clicks "Mark all read" and `POST /api/v1/market/alerts/read-all` returns HTTP 200, THE AlertsPage SHALL set the unread count badge on the AppShell notification bell to 0; IF the call fails, THEN THE AlertsPage SHALL retain the current unread count and display an error message.
8. THE Backend_API SHALL expose `GET /api/v1/market/alerts` returning an array of alert objects with `id`, `ticker`, `alert_type`, `message`, `severity`, `timestamp`, and `is_read`.
9. THE Backend_API SHALL expose `DELETE /api/v1/market/alerts/{id}` that deletes a specific alert and returns HTTP 204, or HTTP 404 if the alert does not exist.
10. THE Backend_API SHALL expose `POST /api/v1/market/alerts/read-all` that marks all alerts as read and returns HTTP 200.
11. IF the `GET /api/v1/market/alerts` response is empty, THEN THE AlertsPage SHALL display an empty-state illustration and the message "No active alerts."

---

### Requirement 9: Watchlist Page Enhancement

**User Story:** As an investor, I want an enhanced Watchlist page, so that I can manage my tracked stocks with inline quotes, predictions, and quick-add functionality.

#### Acceptance Criteria

1. THE WatchlistPage SHALL display all watchlist tickers with live quote data (price, change %, volume) fetched via `GET /api/v1/market/quote/{ticker}` for each ticker; IF a per-ticker quote fetch fails, THEN THE WatchlistPage SHALL display "--" placeholders for that ticker's price, change %, and volume.
2. THE WatchlistPage SHALL display an inline `ConfidenceBar` for each watchlist item showing the AI prediction confidence.
3. WHEN the user clicks a watchlist item row, THE WatchlistPage SHALL navigate to `/stock/{ticker}`.
4. THE WatchlistPage SHALL render an "Add ticker" input at the top accepting up to 10 uppercase alphanumeric characters that calls `POST /api/v1/watchlist` on submission and appends the new ticker to the list with a Framer_Motion entrance animation.
5. WHEN a ticker is added that does not exist as a valid symbol, THE WatchlistPage SHALL display an inline error "Invalid ticker symbol."
6. THE WatchlistPage SHALL render a remove icon on each row that calls `DELETE /api/v1/watchlist/{ticker}` on click after a confirmation tooltip that auto-dismisses after 2 seconds without action.
7. IF the watchlist is empty, THEN THE WatchlistPage SHALL display an empty-state card with a prompt to search for and add a ticker.

---

### Requirement 10: Dashboard Page Enhancement

**User Story:** As a trader, I want my Dashboard to include quick links to the new market analysis pages, so that I can jump to any section without navigating the sidebar.

#### Acceptance Criteria

1. THE DashboardPage SHALL render quick-link cards for Daily Market Brief, Penny Stocks, News Feed, and Alerts in addition to the existing Portfolio, Watchlist, and Trading links.
2. THE DashboardPage SHALL display a "Market Snapshot" section with three metric cards showing S&P 500 change %, NASDAQ change %, and VIX level, fetched via `GET /api/v1/market/snapshot`.
3. THE DashboardPage SHALL display the top 3 daily gainers and top 3 daily losers as compact inline rows sourced from `GET /api/v1/market/movers`.
4. WHEN market data is unavailable (API error), THE DashboardPage SHALL display "--" placeholders in the Market Snapshot metric cards and empty rows with "--" placeholders in the movers section instead of rendering an error page.
5. THE Backend_API SHALL expose `GET /api/v1/market/snapshot` returning `{ sp500_change_pct, nasdaq_change_pct, vix }`.

---

### Requirement 11: Stock Detail Page Enhancement

**User Story:** As a trader, I want the Stock Detail page to show related news and a technical indicator summary, so that I can make an informed trade decision from one page.

#### Acceptance Criteria

1. THE StockDetailPage SHALL render a "Related News" section below the AI Prediction card showing up to 3 articles sorted by `published_at` descending from `GET /api/v1/market/news/{ticker}`, each with a `SentimentBadge` and title.
2. WHEN a related news article title is clicked, THE StockDetailPage SHALL open the article URL in a new browser tab.
3. THE StockDetailPage SHALL render a "Technical Signals" section showing RSI-14 value, MACD signal (bullish / bearish / neutral), and SMA-50 vs SMA-200 cross status, sourced from `GET /api/v1/market/predict/{ticker}` response fields.
4. THE StockDetailPage SHALL display the market cap, P/E ratio, 52-week high, and 52-week low in the Quick Stats row when the quote data includes those fields.
5. WHEN the quote data does not include market cap or P/E, THE StockDetailPage SHALL render "—" in those stat cards rather than omitting the cards.

---

### Requirement 12: Settings Page

**User Story:** As a user, I want a Settings page, so that I can view system configuration and toggle available feature flags.

#### Acceptance Criteria

1. THE SettingsPage SHALL be served at route `/settings`.
2. THE SettingsPage SHALL display the current app environment, API version, and log level fetched from `GET /api/v1/settings`.
3. THE SettingsPage SHALL render toggle switches for available feature flags (Real-Time Streaming, Deep Learning, Alternative Data).
4. WHEN a feature flag toggle is changed, THE SettingsPage SHALL disable the toggle during the in-flight `PATCH /api/v1/settings` request, then display a success toast via Sonner on HTTP 200.
5. WHEN the `PATCH /api/v1/settings` call fails, THE SettingsPage SHALL display an error toast and revert the toggle to its previous state.
6. THE Backend_API SHALL expose `GET /api/v1/settings` returning `{ app_env, api_version, log_level, feature_flags: { real_time_streaming, deep_learning, alternative_data } }`.
7. THE Backend_API SHALL expose `PATCH /api/v1/settings` accepting a partial feature-flags object and persisting the changes, returning HTTP 200 with the updated settings.

---

### Requirement 13: Route Registration and Code-Splitting

**User Story:** As a developer, I want all new pages registered in the React Router config with lazy loading, so that the initial bundle size stays small.

#### Acceptance Criteria

1. THE React_App SHALL register routes `/market`, `/penny-stocks`, `/news`, `/predictions`, `/alerts`, and `/settings` with `React.lazy` and `Suspense` wrappers, each `Suspense` boundary displaying a full-page loading spinner fallback.
2. THE React_App SHALL wrap each lazy-loaded page in `ProtectedRoute` so unauthenticated users are redirected to `/login`.
3. WHEN a user navigates to `/`, THE React_App SHALL redirect to `/market` if the user is authenticated, and to `/login` if not.
4. WHEN a route does not match any registered path, THE React_App SHALL render a 404 page with a "Go to Dashboard" link.
5. THE React_App SHALL register new TanStack_Query query keys for `movers`, `news`, `penny-stocks`, `predictions`, `alerts`, and `snapshot` in the existing `queryKeys` map.

---

### Requirement 14: Correctness Properties

**User Story:** As a developer, I want property-based and integration tests for critical UI data transformations, so that edge cases are caught before they reach users.

#### Acceptance Criteria

1. FOR ALL valid `SentimentScore` values in [-1, 1], THE `SentimentBadge` component SHALL render exactly one badge with a non-empty colour class.
2. FOR ALL `ConfidenceScore` values in [0, 1], THE `ConfidenceBar` component SHALL render a bar with width bounded in [0%, 100%] and `aria-valuenow` reflecting the displayed percentage value.
3. FOR ALL arrays of penny stock rows, THE `MomentumTable` sort function SHALL produce a list where every element's `momentum_score` is >= the momentum_score of every subsequent element when sorted descending (invariant property).
4. FOR ALL arrays of penny stock rows and any non-negative `limit`, THE `select_top_penny_stocks` equivalent client function SHALL return a result whose length is `min(rows.length, limit)` (metamorphic property).
5. FOR ALL news article arrays, the filter function that selects only `is_breaking: true` articles SHALL produce a result that is a subset of the original array with every element satisfying `is_breaking === true` (invariant property).
6. FOR ALL `AccordionRow` expand/collapse cycles, the final DOM state after an even number of toggles SHALL equal the initial DOM state (idempotence property: toggle twice = no net change).
7. FOR ALL valid quote API responses, serialising the response to JSON and parsing it back SHALL produce an object where all numeric fields differ by no more than 0.001 (round-trip property for JSON serialisation).
8. WHEN `ConfidenceBar` receives `value = 0`, THE React_App SHALL render a bar with `aria-valuenow="0"` and width `0%` (edge case).
9. WHEN `ConfidenceBar` receives `value = 100`, THE React_App SHALL render a bar with `aria-valuenow="100"` and width `100%` (edge case).
10. WHEN `SentimentBadge` receives `score = 0` (exactly neutral boundary), THE React_App SHALL render the yellow neutral badge (edge case).
