export const queryKeys = {
  portfolio: {
    summary: () => ['portfolio', 'summary'] as const,
    positions: () => ['portfolio', 'positions'] as const,
    history: () => ['portfolio', 'history'] as const,
  },
  trading: {
    account: () => ['trading', 'account'] as const,
    orders: () => ['trading', 'orders'] as const,
  },
  watchlist: {
    items: () => ['watchlist', 'items'] as const,
    lists: () => ['watchlist', 'lists'] as const,
  },
  market: {
    quote: (ticker: string) => ['market', 'quote', ticker] as const,
    chart: (ticker: string, period?: string) => ['market', 'chart', ticker, period] as const,
    prediction: (ticker: string) => ['market', 'prediction', ticker] as const,
    movers: () => ['market', 'movers'] as const,
    news: (params?: object) => ['market', 'news', params] as const,
    tickerNews: (ticker: string) => ['market', 'news', ticker] as const,
    predictions: (tickers?: string[]) => ['market', 'predictions', tickers] as const,
    pennyStocks: () => ['market', 'penny-stocks'] as const,
    snapshot: () => ['market', 'snapshot'] as const,
    earnings: (ticker: string) => ['market', 'earnings', ticker] as const,
    institutional: (ticker: string) => ['market', 'institutional', ticker] as const,
  },
  alerts: {
    list: () => ['alerts', 'list'] as const,
  },
  settings: {
    config: () => ['settings', 'config'] as const,
  },
}
