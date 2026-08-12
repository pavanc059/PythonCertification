"""
News Categorization Demo

Demonstrates the news categorization functionality without requiring
Redis or database connectivity.
"""

from datetime import datetime, timedelta
from stockiq.data.models import NewsArticle, NewsCategory
from stockiq.news.nlp.categorization import CATEGORY_KEYWORDS, TICKER_PATTERNS
import re


def demo_category_keywords():
    """Demonstrate category keyword definitions."""
    print("=" * 60)
    print("CATEGORY KEYWORDS")
    print("=" * 60)
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        print(f"\n{category.value.upper()}:")
        sample_keywords = list(keywords)[:8]  # Show first 8 keywords
        print(f"  Keywords: {', '.join(sample_keywords)}")
        print(f"  Total: {len(keywords)} keywords")


def demo_ticker_extraction():
    """Demonstrate ticker extraction patterns."""
    print("\n" + "=" * 60)
    print("TICKER EXTRACTION")
    print("=" * 60)
    
    test_texts = [
        "Apple ($AAPL) rose 5% today on strong earnings.",
        "Tesla (NASDAQ:TSLA) announced new vehicle production.",
        "MSFT stock gained while GOOG shares declined.",
        "Microsoft and Google announced partnership.",
    ]
    
    patterns = [re.compile(p, re.IGNORECASE) for p in TICKER_PATTERNS]
    
    for text in test_texts:
        print(f"\nText: {text}")
        extracted = set()
        
        for pattern in patterns:
            matches = pattern.findall(text)
            extracted.update(match.upper() for match in matches)
        
        if extracted:
            print(f"  Extracted: {', '.join(sorted(extracted))}")
        else:
            print(f"  Extracted: (none)")


def demo_manual_categorization():
    """Demonstrate manual categorization logic."""
    print("\n" + "=" * 60)
    print("MANUAL CATEGORIZATION")
    print("=" * 60)
    
    test_articles = [
        {
            "title": "Apple Reports Record Q2 Earnings",
            "content": "Apple Inc. reported quarterly earnings of $1.52 per share, "
                      "beating analyst expectations. Revenue rose 8% to $94.8 billion.",
            "expected_category": NewsCategory.EARNINGS
        },
        {
            "title": "Microsoft Announces Acquisition",
            "content": "Microsoft Corporation announced it will acquire Activision "
                      "Blizzard in a $68.7 billion deal, marking one of the largest "
                      "acquisitions in tech history.",
            "expected_category": NewsCategory.MA
        },
        {
            "title": "FDA Approves New Cancer Drug",
            "content": "The Food and Drug Administration approved a breakthrough drug "
                      "for lung cancer treatment, following clinical trials.",
            "expected_category": NewsCategory.REGULATORY
        },
        {
            "title": "Fed Raises Interest Rates",
            "content": "The Federal Reserve announced a 25 basis point increase in "
                      "interest rates, citing persistent inflation concerns.",
            "expected_category": NewsCategory.ECONOMIC
        },
        {
            "title": "Technology Sector Rallies",
            "content": "The technology sector posted strong gains as semiconductor "
                      "companies rallied on improved supply chain outlook.",
            "expected_category": NewsCategory.SECTOR_SPECIFIC
        },
    ]
    
    for test in test_articles:
        print(f"\nTitle: {test['title']}")
        
        # Combine title and content (weight title more)
        search_text = f"{test['title']} {test['title']} {test['content']}"
        search_text_lower = search_text.lower()
        
        # Count matches for each category
        category_scores = {}
        for category, keywords in CATEGORY_KEYWORDS.items():
            matches = []
            for keyword in keywords:
                if ' ' not in keyword:
                    # Single word - use word boundary
                    pattern = r'\b' + re.escape(keyword) + r'\b'
                    if re.search(pattern, search_text_lower):
                        matches.append(keyword)
                else:
                    # Multi-word - exact phrase
                    if keyword in search_text_lower:
                        matches.append(keyword)
            
            if matches:
                word_count = len(search_text.split())
                confidence = (len(matches) / word_count * 100)
                category_scores[category] = (confidence, matches)
        
        # Select best category
        if category_scores:
            best = max(category_scores.items(), key=lambda x: x[1][0])
            selected_category = best[0]
            confidence = best[1][0]
            matched_keywords = best[1][1]
            
            print(f"  Predicted: {selected_category.value}")
            print(f"  Confidence: {confidence:.2f}%")
            print(f"  Matched keywords: {', '.join(matched_keywords[:5])}")
            print(f"  Expected: {test['expected_category'].value}")
            
            if selected_category == test['expected_category']:
                print(f"  Result: ✓ CORRECT")
            else:
                print(f"  Result: ✗ INCORRECT")
        else:
            print(f"  Predicted: GENERAL (no keywords matched)")


def demo_relevance_factors():
    """Demonstrate relevance scoring factors."""
    print("\n" + "=" * 60)
    print("RELEVANCE SCORING FACTORS")
    print("=" * 60)
    
    print("\nRelevance is calculated based on four factors:")
    print("\n1. Ticker Overlap (40%)")
    print("   - How many tickers in article match user's watchlist")
    print("   - Example: User watches AAPL, article mentions AAPL → 0.4 points")
    
    print("\n2. Category Match (30%)")
    print("   - Does article category match user's interests")
    print("   - Example: User interested in 'earnings', article is EARNINGS → 0.3 points")
    
    print("\n3. Source Credibility (20%)")
    print("   - Is the source a trusted news outlet")
    print("   - High credibility: Reuters, Bloomberg, WSJ, FT, CNBC, MarketWatch")
    print("   - Example: Article from Reuters → 0.2 points")
    
    print("\n4. Recency (10%)")
    print("   - How recent is the article")
    print("   - Recent articles (< 12 hours) get higher scores")
    print("   - Example: Article from 2 hours ago → ~0.08 points")
    
    print("\nTotal Relevance Score: 0.0 to 1.0")
    print("Higher scores = more relevant to user interests")


def demo_breaking_news():
    """Demonstrate breaking news detection."""
    print("\n" + "=" * 60)
    print("BREAKING NEWS DETECTION")
    print("=" * 60)
    
    test_cases = [
        {"minutes_ago": 5, "expected": True},
        {"minutes_ago": 20, "expected": True},
        {"minutes_ago": 35, "expected": False},
        {"minutes_ago": 120, "expected": False},
    ]
    
    print("\nProperty 10: An article is breaking news if published")
    print("within the last 30 minutes (1800 seconds).")
    
    for test in test_cases:
        minutes = test["minutes_ago"]
        published_at = datetime.utcnow() - timedelta(minutes=minutes)
        age_seconds = (datetime.utcnow() - published_at).total_seconds()
        is_breaking = age_seconds <= 1800
        
        status = "✓ BREAKING" if is_breaking else "  Normal"
        expected = "✓" if is_breaking == test["expected"] else "✗"
        
        print(f"\n{expected} {minutes} minutes ago: {status}")
        print(f"   Age: {int(age_seconds)} seconds")


def main():
    """Run all demonstrations."""
    print("\n" + "=" * 60)
    print("NEWS CATEGORIZATION DEMO")
    print("=" * 60)
    print("\nDemonstrating news categorization functionality")
    print("(No Redis or database required)")
    
    demo_category_keywords()
    demo_ticker_extraction()
    demo_manual_categorization()
    demo_relevance_factors()
    demo_breaking_news()
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETE")
    print("=" * 60)
    print("\nFor full functionality with caching and database validation,")
    print("use the NewsCategorizer class with Redis and PostgreSQL running.")
    print()


if __name__ == "__main__":
    main()
