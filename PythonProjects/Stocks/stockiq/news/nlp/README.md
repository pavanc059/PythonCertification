# News NLP Module

Natural language processing components for news analysis.

## Overview

This module provides NLP functionality for analyzing financial news articles:

- **News Categorization**: Keyword-based classification into predefined categories
- **Ticker Extraction**: Regex and NER-based extraction of stock ticker symbols
- **Relevance Scoring**: Personalized ranking based on user interests
- **Redis Caching**: Performance optimization through result caching

## Components

### NewsCategorizer

Main class for news categorization and analysis.

```python
from stockiq.news.nlp.categorization import NewsCategorizer
from stockiq.data.models import NewsArticle

categorizer = NewsCategorizer()

# Categorize an article
category = categorizer.categorize_article(article)

# Extract tickers from text
tickers = categorizer.extract_tickers("Apple ($AAPL) and Tesla (NASDAQ:TSLA) rose today")

# Calculate relevance score
score = categorizer.calculate_relevance_score(article, user_interests=['AAPL', 'earnings'])

# Rank articles by relevance
ranked = categorizer.rank_by_relevance(articles, user_interests=['AAPL', 'technology'])
```

### Categories

Articles are classified into the following categories:

- **EARNINGS**: Quarterly results, earnings reports, financial statements
- **M&A**: Mergers, acquisitions, takeovers, strategic partnerships
- **REGULATORY**: FDA approvals, SEC investigations, legal actions
- **ECONOMIC**: Fed policy, GDP, inflation, unemployment, economic indicators
- **SECTOR_SPECIFIC**: Industry and sector-specific developments
- **GENERAL**: General market news that doesn't fit other categories

## Keyword-Based Classification

The categorizer uses keyword matching to classify articles:

1. **Keyword Matching**: Searches for category-specific keywords in title and content
2. **Confidence Scoring**: Calculates confidence based on keyword density
3. **Category Selection**: Selects category with highest confidence score
4. **Default Handling**: Assigns GENERAL category if no clear match

### Example Categories

**Earnings Keywords**: earnings, revenue, profit, loss, quarterly, eps, guidance, forecast

**M&A Keywords**: merger, acquisition, takeover, buyout, deal, consolidation

**Regulatory Keywords**: fda, sec, investigation, lawsuit, approval, recall, fine

**Economic Keywords**: gdp, inflation, fed, interest rate, unemployment, jobs report

## Ticker Extraction

Extracts stock ticker symbols using multiple regex patterns:

### Supported Formats

1. **Dollar Format**: `$AAPL`, `$TSLA`
2. **Exchange Format**: `(NASDAQ:AAPL)`, `(NYSE:MSFT)`
3. **Contextual**: `AAPL stock`, `TSLA shares`

### Validation

Extracted tickers are validated against the stocks database to filter out false positives.

```python
# Extract tickers from text
text = "Apple ($AAPL) and Tesla (NASDAQ:TSLA) stocks rose today"
tickers = categorizer.extract_tickers(text)
# Returns: ['AAPL', 'TSLA']
```

## Relevance Scoring

Calculates how relevant an article is to user interests:

### Relevance Factors

1. **Ticker Overlap (40%)**: Mentioned tickers match user watchlist
2. **Category Match (30%)**: Article category matches user interests
3. **Source Credibility (20%)**: Trusted news sources ranked higher
4. **Recency (10%)**: More recent articles ranked higher

### High Credibility Sources

- Reuters
- Bloomberg
- Wall Street Journal (WSJ)
- Financial Times (FT)
- CNBC
- MarketWatch

```python
# Calculate relevance for specific interests
user_interests = ["AAPL", "earnings", "reuters"]
score = categorizer.calculate_relevance_score(article, user_interests)
# Returns: 0.0-1.0 score
```

## Ranking

Ranks articles by relevance in descending order (Property 11):

### With User Interests

Personalized ranking based on ticker matches, category preferences, and source preferences.

```python
ranked = categorizer.rank_by_relevance(articles, user_interests=['AAPL', 'technology'])
```

### Without User Interests

Default ranking based on:
1. Breaking news (published within 30 minutes)
2. Source credibility
3. Recency

```python
ranked = categorizer.rank_by_relevance(articles)
```

## Caching

Results are cached in Redis for performance:

- **Category Cache**: 24 hours (articles don't change category)
- **Relevance Cache**: 1 hour (user interests may change)
- **Ticker Validation**: 1 hour (stock list rarely changes)

### Cache Management

```python
# Clear cache for specific article
categorizer.clear_cache(article_id="article_123")

# Clear all categorization caches
categorizer.clear_cache()
```

## Requirements Implemented

- **Requirement 2.2**: Categorize news by topic
- **Requirement 2.3**: Extract mentioned stock tickers from news articles
- **Requirement 2.6**: Rank news articles by relevance score

## Properties Validated

- **Property 8**: News category assignment (each article gets exactly one category)
- **Property 11**: News relevance ranking (articles sorted by relevance score)

## Dependencies

- `re`: Regular expression matching
- `structlog`: Structured logging
- `SQLAlchemy`: Database access (for ticker validation)
- `Redis`: Caching (via stockiq.infrastructure.cache)

## Testing

### Full Tests (requires Redis and Database)

```bash
pytest tests/test_news_categorization.py -v
```

### Standalone Tests (no external dependencies)

```bash
python tests/test_news_categorization_standalone.py
```

## Performance

- **Categorization**: O(n) where n is article length
- **Ticker Extraction**: O(n) where n is text length
- **Relevance Scoring**: O(1) with caching, O(k) without (k = interest count)
- **Ranking**: O(n log n) where n is article count

## Usage Example

```python
from stockiq.news.nlp.categorization import NewsCategorizer
from stockiq.data.collectors.news import NewsCollector
from stockiq.data.models import NewsArticle

# Initialize
collector = NewsCollector()
categorizer = NewsCategorizer()

# Collect news
articles = collector.collect_latest_news(limit=100)

# Categorize and extract tickers
for article in articles:
    category = categorizer.categorize_article(article)
    tickers = categorizer.extract_tickers(article.content)
    print(f"{article.title} - Category: {category.value}, Tickers: {tickers}")

# Rank by user interests
user_interests = ["AAPL", "TSLA", "earnings", "technology"]
ranked_articles = categorizer.rank_by_relevance(articles, user_interests)

# Display top 10 most relevant
for i, article in enumerate(ranked_articles[:10], 1):
    score = categorizer.calculate_relevance_score(article, user_interests)
    print(f"{i}. [{score:.2f}] {article.title}")
```

## Future Enhancements

- [ ] Add spaCy NER for improved entity extraction
- [ ] Implement abstractive summarization for article summaries
- [ ] Add sentiment analysis integration
- [ ] Support multi-label classification (articles can have multiple categories)
- [ ] Add machine learning-based categorization (vs. keyword-based)
- [ ] Implement language detection and multi-language support
