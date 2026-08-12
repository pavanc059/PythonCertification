"""
Entity Extraction Demo

Demonstrates the EntityExtractor functionality for extracting:
- Companies (ORG entities)
- People (PERSON entities)
- Locations (GPE, LOC entities)
- Stock tickers (regex + database validation)

Requirements demonstrated:
- Requirement 2.3: Extract mentioned stock tickers from news articles
- Requirement 2.7: Extract key entities from news articles
"""

from stockiq.news.nlp.entities import EntityExtractor, get_entity_extractor


def demo_basic_extraction():
    """Demonstrate basic entity extraction."""
    print("=" * 70)
    print("DEMO 1: Basic Entity Extraction")
    print("=" * 70)
    
    # Initialize extractor
    extractor = EntityExtractor()
    
    # Sample news article
    article_text = """
    Apple Inc. ($AAPL) CEO Tim Cook announced record-breaking quarterly 
    earnings today at the company's Cupertino headquarters. The tech giant 
    reported revenue of $123.9 billion, beating Wall Street expectations.
    
    Goldman Sachs analyst Sarah Johnson upgraded the stock to buy, citing 
    strong iPhone sales in China and growing services revenue. Microsoft 
    (NASDAQ:MSFT) and Tesla also saw gains following Apple's announcement.
    
    The earnings call featured CFO Luca Maestri discussing margin expansion 
    and future investments in artificial intelligence. Trading was active 
    across New York, London, and Hong Kong exchanges.
    """
    
    print("\nArticle Text:")
    print(article_text)
    
    # Extract entities
    print("\nExtracting entities...")
    entities = extractor.extract_entities(article_text)
    
    # Display results
    print("\n" + "-" * 70)
    print("EXTRACTION RESULTS")
    print("-" * 70)
    print(f"\n📊 Companies ({len(entities.companies)}):")
    for company in entities.companies:
        print(f"   • {company}")
    
    print(f"\n👤 People ({len(entities.people)}):")
    for person in entities.people:
        print(f"   • {person}")
    
    print(f"\n📍 Locations ({len(entities.locations)}):")
    for location in entities.locations:
        print(f"   • {location}")
    
    print(f"\n💹 Tickers ({len(entities.tickers)}):")
    for ticker in entities.tickers:
        print(f"   • ${ticker}")
    
    if not entities.tickers:
        print("   (Note: No tickers validated - database may be empty)")


def demo_ticker_extraction():
    """Demonstrate ticker extraction with various formats."""
    print("\n\n" + "=" * 70)
    print("DEMO 2: Ticker Extraction Patterns")
    print("=" * 70)
    
    extractor = EntityExtractor()
    
    test_cases = [
        ("Apple ($AAPL) gained 5% today", "Dollar sign format: $AAPL"),
        ("Tesla (NASDAQ:TSLA) announced new models", "Exchange format: NASDAQ:TSLA"),
        ("MSFT stock reached new highs", "Contextual format: MSFT stock"),
        ("GOOGL:US traded higher in premarket", "Country code format: GOOGL:US"),
        ("$AMZN and $NVDA led tech sector gains", "Multiple tickers"),
    ]
    
    print("\nTesting various ticker formats:\n")
    
    for text, description in test_cases:
        tickers = extractor.extract_tickers(text)
        print(f"Format: {description}")
        print(f"  Text:     '{text}'")
        print(f"  Extracted: {tickers if tickers else '(none - needs database)'}")
        print()


def demo_article_processing():
    """Demonstrate article-level entity extraction with caching."""
    print("\n" + "=" * 70)
    print("DEMO 3: Article Processing with Caching")
    print("=" * 70)
    
    extractor = get_entity_extractor()  # Use global instance
    
    article_id = "news_12345"
    article_text = """
    Amazon (NASDAQ:AMZN) founder Jeff Bezos announced plans to invest 
    $10 billion in climate initiatives. The Seattle-based company will 
    partner with environmental organizations across California, Texas, 
    and New York to fund renewable energy projects.
    """
    
    print("\nProcessing article:", article_id)
    print("Text:", article_text.strip()[:100] + "...")
    
    # First extraction (will cache result)
    print("\n1st extraction (caches result)...")
    entities1 = extractor.extract_entities_from_article(article_id, article_text)
    
    # Second extraction (uses cache)
    print("2nd extraction (uses cache)...")
    entities2 = extractor.extract_entities_from_article(article_id, article_text)
    
    print("\nResults:")
    print(f"  Companies: {entities1.companies}")
    print(f"  People:    {entities1.people}")
    print(f"  Locations: {entities1.locations}")
    print(f"  Tickers:   {entities1.tickers if entities1.tickers else '(needs database)'}")
    
    # Results should be identical
    print("\nCache validation:", "✓ PASS" if entities1.to_dict() == entities2.to_dict() else "✗ FAIL")


def demo_batch_processing():
    """Demonstrate batch entity extraction."""
    print("\n" + "=" * 70)
    print("DEMO 4: Batch Processing")
    print("=" * 70)
    
    extractor = EntityExtractor()
    
    articles = [
        "Apple CEO Tim Cook visited Cupertino factory.",
        "Microsoft announced partnership with OpenAI.",
        "Tesla opened new Gigafactory in Austin, Texas.",
    ]
    
    print("\nProcessing multiple articles at once:\n")
    
    # Batch process
    results = extractor.extract_batch(articles)
    
    for i, (text, entities) in enumerate(zip(articles, results), 1):
        print(f"Article {i}: {text}")
        print(f"  Companies: {entities.companies}")
        print(f"  People:    {entities.people}")
        print(f"  Locations: {entities.locations}")
        print()


def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("ENTITY EXTRACTION DEMONSTRATION")
    print("=" * 70)
    print("\nThis demo showcases the EntityExtractor class for extracting")
    print("structured information from financial news articles.")
    print("\nFeatures:")
    print("  • Named Entity Recognition (NER) using spaCy")
    print("  • Multi-pattern ticker extraction")
    print("  • Database validation for tickers")
    print("  • Redis caching for performance")
    print("  • Batch processing support")
    
    try:
        demo_basic_extraction()
        demo_ticker_extraction()
        demo_article_processing()
        demo_batch_processing()
        
        print("\n" + "=" * 70)
        print("✓ Demo completed successfully!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
