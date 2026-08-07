"""
NLP components for news analysis.

This module provides natural language processing functionality for:
- News categorization and classification
- Ticker extraction from text
- Entity recognition (companies, people, locations)
- Sentiment analysis
- Text summarization
"""

from .categorization import NewsCategorizer, extract_tickers
from .entities import EntityExtractor, Entities, get_entity_extractor

__all__ = [
    'NewsCategorizer',
    'extract_tickers',
    'EntityExtractor',
    'Entities',
    'get_entity_extractor',
]
