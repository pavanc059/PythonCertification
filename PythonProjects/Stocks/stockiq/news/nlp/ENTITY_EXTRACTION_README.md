# Entity Extraction Module

## Overview

The Entity Extraction module provides Named Entity Recognition (NER) capabilities for financial news articles using spaCy. It extracts structured information from unstructured text, including companies, people, locations, and stock tickers.

## Requirements Implemented

- **Requirement 2.3**: Extract mentioned stock tickers from news articles using NLP
- **Requirement 2.7**: Extract key entities (companies, people, locations) from news articles

## Features

### Entity Types

1. **Companies** (ORG entities)
   - Extracted using spaCy's Named Entity Recognition
   - Examples: "Apple Inc.", "Goldman Sachs", "Microsoft"

2. **People** (PERSON entities)
   - Key individuals mentioned in articles
   - Examples: "Tim Cook", "Jeff Bezos", "Elon Musk"

3. **Locations** (GPE, LOC entities)
   - Cities, countries, states, regions
   - Examples: "Cupertino", "New York", "China"

4. **Stock Tickers**
   - Extracted using regex patterns
   - Validated against stocks database
   - Supports multiple formats:
     - Dollar sign: `$AAPL`
     - Exchange: `(NASDAQ:TSLA)`
     - Contextual: `MSFT stock`
     - Country code: `GOOGL:US`

### Technical Features

- **spaCy NER Pipeline**: Uses `en_core_web_sm` model for entity recognition
- **Multi-Pattern Regex**: Handles various ticker formats
- **Database Validation**: Verifies tickers against stocks table
- **Redis Caching**: Automatic caching with 1-hour TTL
- **Batch Processing**: Efficient processing of multiple texts
- **Graceful Degradation**: Works without Redis/PostgreSQL (reduced functionality)

## Installation

### 1. Install spaCy

spaCy is already in `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 2. Download spaCy Model

```bash
python -m spacy download en_core_web_sm
```

### 3. Verify Installation

```bash
python -m spacy info en_core_web_sm
```

## Usage

### Basic Entity Extraction

```python
from stockiq.news.nlp.entities import EntityExtractor

# Initialize extractor
extractor = EntityExtractor()

# Extract entities from text
text = """
Apple Inc. ($AAPL) CEO Tim Cook announced earnings in Cupertino.
Goldman Sachs upgraded the stock following strong iPhone sales in China.
"""

entities = extractor.extract_entities(text)

print(f"Companies: {entities.companies}")  # ['Apple Inc.', 'Goldman Sachs']
print(f"People: {entities.people}")        # ['Tim Cook']
print(f"Locations: {entities.locations}")  # ['Cupertino', 'China']
print(f"Tickers: {entities.tickers}")      # ['AAPL'] (if in database)
```

### Article-Level Extraction (with caching)

```python
from stockiq.news.nlp.entities import EntityExtractor

extractor = EntityExtractor()

# Extract from article (results cached in Redis)
article_id = "news_12345"
article_text = "Full article text here..."

entities = extractor.extract_entities_from_article(
    article_id=article_id,
    text=article_text,
    use_cache=True  # default
)
```

### Ticker-Only Extraction

```python
from stockiq.news.nlp.entities import EntityExtractor

extractor = EntityExtractor()

text = "Apple ($AAPL) and Tesla (NASDAQ:TSLA) stocks rose today"
tickers = extractor.extract_tickers(text)

print(tickers)  # ['AAPL', 'TSLA'] (if validated)
```

### Batch Processing

```python
from stockiq.news.nlp.entities import EntityExtractor

extractor = EntityExtractor()

articles = [
    "Apple CEO Tim Cook visited Cupertino.",
    "Microsoft announced partnership with OpenAI.",
    "Tesla opened factory in Austin, Texas.",
]

# Efficient batch processing using spaCy's pipe
results = extractor.extract_batch(articles)

for article, entities in zip(articles, results):
    print(f"Article: {article}")
    print(f"  Entities: {entities.companies}, {entities.people}, {entities.locations}")
```

### Global Instance

```python
from stockiq.news.nlp.entities import get_entity_extractor

# Get singleton instance
extractor = get_entity_extractor()

# Use as normal
entities = extractor.extract_entities(text)
```

## Data Model

### Entities Class

```python
@dataclass
class Entities:
    companies: List[str]    # ORG entities
    people: List[str]       # PERSON entities
    locations: List[str]    # GPE, LOC entities
    tickers: List[str]      # Validated ticker symbols
    
    def to_dict(self) -> Dict[str, List[str]]:
        """Convert to dictionary for storage."""
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'Entities':
        """Create from dictionary."""
```

## Ticker Extraction Patterns

The module uses multiple regex patterns to extract tickers in various formats:

| Format | Example | Regex Pattern |
|--------|---------|---------------|
| Dollar sign | `$AAPL` | `\$([A-Z]{1,5})\b` |
| Exchange | `(NASDAQ:TSLA)` | `\((?:NASDAQ\|NYSE\|AMEX\|OTC):\s*([A-Z]{1,5})\)` |
| Contextual | `MSFT stock` | `\b([A-Z]{2,5})\s+(?:stock\|shares\|ticker\|symbol)` |
| Country code | `AAPL:US` | `\b([A-Z]{2,5}):(?:US\|NASDAQ\|NYSE)` |

All extracted tickers are:
1. Converted to uppercase
2. Validated against the stocks database
3. Deduplicated
4. Sorted alphabetically

## Caching Strategy

### Cache Keys

- **Text-based**: `entities:text:{hash(text)}`
- **Article-based**: `entities:article:{article_id}`
- **Ticker validation**: `news:valid_tickers`

### TTL Values

- Entity extraction: **1 hour**
- Ticker validation list: **1 hour**

### Cache Behavior

- **Cache miss**: Performs NER and caches result
- **Cache hit**: Returns cached entities immediately
- **No Redis**: Continues without caching (degrades gracefully)

## Integration with News Pipeline

The EntityExtractor integrates with the sentiment analyzer:

```python
from stockiq.news.nlp.sentiment import SentimentAnalyzer
from stockiq.news.nlp.entities import EntityExtractor

sentiment_analyzer = SentimentAnalyzer()
entity_extractor = EntityExtractor()

# Analyze article
article_text = "Full article text..."

# Get sentiment
sentiment = sentiment_analyzer.analyze_sentiment(article_text)

# Extract entities
entities = entity_extractor.extract_entities(article_text)

# Store both together
sentiment_analyzer.store_sentiment(
    article_db_id=article_id,
    stock_db_id=stock_id,
    sentiment=sentiment,
    entities=entities.to_dict()  # Stored as JSONB
)
```

## Performance

### spaCy NER Performance

- **Single text**: ~50-100ms per article
- **Batch processing**: ~20-30ms per article (using pipe)
- **Cache hit**: <1ms

### Ticker Extraction Performance

- **Regex matching**: <5ms per text
- **Database validation**: ~10-20ms (first query, then cached)
- **Cache hit**: <1ms

## Testing

### Run Tests

```bash
# Unit tests
python test_entity_extractor.py

# Demo
python examples/entity_extraction_demo.py
```

### Expected Output

```
✓ PASS: Basic Extraction
✓ PASS: Ticker Extraction
✓ PASS: Global Instance
✓ PASS: Caching
```

## Troubleshooting

### spaCy Model Not Found

**Error**: `Can't find pipeline meta.json`

**Solution**:
```bash
python -m spacy download en_core_web_sm
```

### No Tickers Extracted

**Issue**: Tickers found by regex but not validated

**Causes**:
1. PostgreSQL not running
2. Stocks table is empty
3. Ticker not in database

**Solution**: Ensure database is running and populated:
```bash
python scripts/init_db.py
```

### Redis Connection Failed

**Issue**: Cache operations failing

**Effect**: Continues without caching (slower but functional)

**Solution**: Start Redis server:
```bash
redis-server
```

### "CFO" Extracted as Company

**Issue**: spaCy occasionally misclassifies entities

**Solution**: This is expected behavior. Post-process entities if needed:
```python
# Filter out common false positives
filtered_companies = [
    c for c in entities.companies 
    if c not in ['CFO', 'CEO', 'CTO']
]
```

## Future Enhancements

1. **Custom NER Model**: Fine-tune spaCy on financial news corpus
2. **Entity Linking**: Link companies to stock tickers automatically
3. **Relationship Extraction**: Extract relationships between entities
4. **Event Detection**: Identify events (earnings, M&A, etc.)
5. **Co-reference Resolution**: Link pronouns to entities
6. **Entity Disambiguation**: Resolve ambiguous company names

## Dependencies

- **spaCy** >= 3.6.0: NER framework
- **en_core_web_sm**: English NER model (12.8 MB)
- **Redis**: Caching layer (optional)
- **PostgreSQL**: Ticker validation (optional)
- **structlog**: Structured logging

## API Reference

### EntityExtractor Class

#### Methods

- `extract_entities(text: str) -> Entities`
  - Extract all entities from text
  
- `extract_tickers(text: str) -> List[str]`
  - Extract and validate ticker symbols
  
- `extract_entities_from_article(article_id: str, text: str, use_cache: bool = True) -> Entities`
  - Extract entities with article-level caching
  
- `extract_batch(texts: List[str]) -> List[Entities]`
  - Batch process multiple texts efficiently
  
- `clear_cache(article_id: Optional[str] = None) -> None`
  - Clear entity extraction cache

### Entities Class

#### Attributes

- `companies: List[str]` - ORG entities
- `people: List[str]` - PERSON entities
- `locations: List[str]` - GPE, LOC entities
- `tickers: List[str]` - Validated ticker symbols

#### Methods

- `to_dict() -> Dict[str, List[str]]` - Convert to dictionary
- `from_dict(data: Dict) -> Entities` - Create from dictionary

## License

Part of the Universal Stock Analyzer project.
