"""
Demonstration of news summarization functionality.

This script shows the NewsSummarizer class in action:
- Extractive summarization using TextRank
- Key fact extraction (prices, percentages, dates)
- Daily summary generation from multiple articles
"""

from datetime import datetime
from stockiq.news.nlp.summarization import NewsSummarizer
from stockiq.data.models import NewsArticle


def main():
    # Create summarizer instance
    summarizer = NewsSummarizer()
    
    print("=" * 80)
    print("NEWS SUMMARIZATION DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Sample article
    article = NewsArticle(
        id="demo_001",
        title="Apple Reports Record Quarterly Earnings",
        content=(
            "Apple Inc. reported record quarterly earnings that exceeded analyst expectations, "
            "sending shares up 12% to $175.50 in after-hours trading on January 28, 2024. "
            "The company posted revenue of $119.6 billion, representing a 15% increase year-over-year. "
            "CEO Tim Cook highlighted strong iPhone sales which grew 22% in the quarter to $65.7 billion. "
            "The services segment also performed exceptionally well, generating $23.1 billion in revenue, "
            "a 14% increase from the previous year. "
            "Mac sales surged 18% to $8.5 billion, driven by strong demand for the new MacBook Pro models. "
            "iPad revenue grew 9% to $7.2 billion, while wearables and home products reached $12.4 billion. "
            "Gross margin improved to 44.5%, up from 43.2% in the prior year quarter. "
            "Analysts praised the results and several firms raised their price targets for the stock. "
            "Morgan Stanley analyst Katy Huberty raised her target to $210, citing strong ecosystem momentum. "
            "The company also announced a new $90 billion share buyback program and increased its dividend by 5%. "
            "Looking ahead, management provided optimistic guidance for the next quarter, "
            "expecting revenue between $90 billion and $94 billion. "
            "The company continues to invest heavily in research and development, "
            "spending $7.8 billion in the quarter, up 18% year-over-year. "
            "Cook emphasized Apple's commitment to innovation and expanding its services business."
        ),
        source="Financial Times",
        published_at=datetime(2024, 1, 28, 21, 30),
        url="https://example.com/apple-earnings",
        tickers=["AAPL"]
    )
    
    # 1. Extractive Summarization
    print("1. EXTRACTIVE SUMMARIZATION (TextRank)")
    print("-" * 80)
    print(f"Original Length: {len(article.content)} characters")
    print()
    
    summary = summarizer.summarize_extractive(
        f"{article.title}. {article.content}",
        sentences=3
    )
    
    print(f"Summary ({len(summary)} characters):")
    print(summary)
    print()
    print()
    
    # 2. Key Fact Extraction
    print("2. KEY FACT EXTRACTION")
    print("-" * 80)
    
    facts = summarizer.extract_key_facts(article.content)
    
    print(f"Prices Extracted: {len(facts.prices)}")
    for i, price in enumerate(facts.prices[:5], 1):
        print(f"  {i}. ${price['value']:,.2f} - {price['context'][:50]}...")
    print()
    
    print(f"Percentages Extracted: {len(facts.percentages)}")
    for i, pct in enumerate(facts.percentages[:5], 1):
        print(f"  {i}. {pct['value']}% - {pct['context'][:50]}...")
    print()
    
    print(f"Dates Extracted: {len(facts.dates)}")
    for i, date in enumerate(facts.dates[:5], 1):
        print(f"  {i}. {date['value']} - {date['context'][:50]}...")
    print()
    
    print(f"Numbers Extracted: {len(facts.numbers)}")
    for i, num in enumerate(facts.numbers[:5], 1):
        print(f"  {i}. {num['value']:,.0f} {num['unit']} - {num['context'][:40]}...")
    print()
    print()
    
    # 3. Article Summarization with Facts
    print("3. COMPREHENSIVE ARTICLE SUMMARY")
    print("-" * 80)
    
    result = summarizer.summarize_article(
        article,
        sentences=2,
        include_facts=True
    )
    
    print(f"Article ID: {result['article_id']}")
    print(f"Summary: {result['summary']}")
    print(f"Compression Ratio: {result['summary_length']}/{result['original_length']} "
          f"({result['summary_length']/result['original_length']*100:.1f}%)")
    print()
    print()
    
    # 4. Daily Summary Generation
    print("4. DAILY MARKET SUMMARY")
    print("-" * 80)
    
    # Create a few more sample articles
    articles = [
        article,
        NewsArticle(
            id="demo_002",
            title="Tesla Delivers Record Number of Vehicles",
            content=(
                "Tesla Inc. announced record quarterly vehicle deliveries of 484,507 units, "
                "exceeding analyst estimates of 473,000 units. "
                "The company produced 495,000 vehicles in the quarter. "
                "Model 3 and Model Y accounted for 461,538 deliveries. "
                "The strong results sent shares up 8% in pre-market trading."
            ),
            source="Reuters",
            published_at=datetime(2024, 1, 28, 20, 0),
            url="https://example.com/tesla-deliveries",
            tickers=["TSLA"]
        ),
        NewsArticle(
            id="demo_003",
            title="Fed Signals Potential Rate Cut in March",
            content=(
                "Federal Reserve officials signaled the possibility of a 25 basis point rate cut "
                "at their March meeting, citing cooling inflation data. "
                "The Consumer Price Index rose 2.4% year-over-year in December, "
                "down from 2.7% in November. "
                "Market participants are pricing in an 85% probability of a rate cut."
            ),
            source="Bloomberg",
            published_at=datetime(2024, 1, 28, 19, 30),
            url="https://example.com/fed-rate-cut",
            tickers=[]
        )
    ]
    
    daily_summary = summarizer.generate_daily_summary(articles)
    
    print(daily_summary)
    print()
    print()
    
    # 5. TextRank Algorithm Demonstration
    print("5. TEXTRANK ALGORITHM VISUALIZATION")
    print("-" * 80)
    
    test_text = (
        "The stock market experienced significant volatility today. "
        "Technology stocks led the gains with a 3% increase. "
        "Energy sector stocks also rose by 2.5% on oil price strength. "
        "Healthcare stocks declined slightly by 0.8% amid regulatory concerns. "
        "Overall market sentiment remained cautiously optimistic."
    )
    
    sentences = summarizer._tokenize_sentences(test_text)
    print(f"Original Sentences: {len(sentences)}")
    for i, sent in enumerate(sentences, 1):
        print(f"  {i}. {sent}")
    print()
    
    # Build similarity matrix
    sim_matrix = summarizer._build_similarity_matrix(sentences)
    print("Similarity Matrix (showing first 3x3):")
    for i in range(min(3, len(sim_matrix))):
        print(f"  {sim_matrix[i][:3]}")
    print()
    
    # Apply TextRank
    scores = summarizer._textrank(sim_matrix)
    print("TextRank Scores:")
    for i, score in enumerate(scores, 1):
        print(f"  Sentence {i}: {score:.4f}")
    print()
    
    # Get top 2 sentences
    summary = summarizer.summarize_extractive(test_text, sentences=2)
    print(f"Summary (2 sentences): {summary}")
    print()
    
    print("=" * 80)
    print("DEMONSTRATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
