"""
Test sentiment analyzer with FinBERT loaded from local directory.
"""

from stockiq.news.nlp.sentiment import get_sentiment_analyzer

print("=" * 60)
print("SENTIMENT ANALYZER TEST - FinBERT Local Model")
print("=" * 60)

print("\nInitializing sentiment analyzer...")
analyzer = get_sentiment_analyzer()

print(f"\n✓ VADER initialized: {analyzer.vader is not None}")
print(f"✓ FinBERT Tokenizer initialized: {analyzer.finbert_tokenizer is not None}")
print(f"✓ FinBERT Model initialized: {analyzer.finbert_model is not None}")

# Test cases
test_cases = [
    {
        "name": "Positive Financial News",
        "text": "Apple reports record-breaking quarterly earnings with strong iPhone sales growth!"
    },
    {
        "name": "Negative Financial News",
        "text": "Company announces massive layoffs and reports significant quarterly losses."
    },
    {
        "name": "Neutral Financial News",
        "text": "The stock price closed at 150 dollars per share today."
    },
    {
        "name": "Strong Positive",
        "text": "Outstanding revenue growth exceeds analyst expectations with excellent profit margins."
    },
    {
        "name": "Strong Negative",
        "text": "Devastating financial results with bankruptcy fears and severe operational problems."
    }
]

print("\n" + "=" * 60)
print("SENTIMENT ANALYSIS RESULTS")
print("=" * 60)

for i, test in enumerate(test_cases, 1):
    print(f"\n[Test {i}] {test['name']}")
    print(f"Text: {test['text']}")
    print("-" * 60)
    
    result = analyzer.analyze_sentiment(test['text'])
    
    print(f"Overall Score:   {result.overall:>6.3f}")
    print(f"VADER Score:     {result.vader_score:>6.3f}")
    print(f"FinBERT Score:   {result.finbert_score:>6.3f}")
    print(f"Confidence:      {result.confidence:>6.3f}")
    
    # Interpret sentiment
    if result.overall > 0.3:
        sentiment = "POSITIVE"
    elif result.overall < -0.3:
        sentiment = "NEGATIVE"
    else:
        sentiment = "NEUTRAL"
    
    print(f"Interpretation:  {sentiment}")

print("\n" + "=" * 60)
print("✓ All tests completed successfully!")
print("=" * 60)
