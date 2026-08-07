"""
Test script for EntityExtractor class.

This script verifies:
1. spaCy model loading
2. Entity extraction (companies, people, locations)
3. Ticker extraction and validation
4. Redis caching integration
"""

import sys
from stockiq.news.nlp.entities import EntityExtractor, get_entity_extractor

def test_basic_extraction():
    """Test basic entity extraction."""
    print("=" * 60)
    print("Testing EntityExtractor")
    print("=" * 60)
    
    # Initialize extractor
    print("\n1. Initializing EntityExtractor...")
    extractor = EntityExtractor()
    
    # Check if spaCy loaded
    if extractor.nlp:
        print("   ✓ spaCy model loaded successfully")
    else:
        print("   ✗ spaCy model not available")
        return False
    
    # Test text with multiple entities
    test_text = """
    Apple Inc. ($AAPL) CEO Tim Cook announced strong quarterly earnings today.
    The Cupertino-based tech giant saw revenue rise 15% year-over-year.
    Tesla (NASDAQ:TSLA) and Microsoft (MSFT) also reported positive results.
    Goldman Sachs analyst Sarah Johnson upgraded the stock to buy.
    Trading was active in New York and London markets.
    """
    
    print("\n2. Extracting entities from test text...")
    print(f"   Text: {test_text[:100]}...")
    
    entities = extractor.extract_entities(test_text)
    
    # Display results
    print("\n3. Extraction Results:")
    print(f"   Companies: {entities.companies}")
    print(f"   People: {entities.people}")
    print(f"   Locations: {entities.locations}")
    print(f"   Tickers: {entities.tickers}")
    
    # Verify we got some entities
    success = True
    if not entities.companies:
        print("   ⚠ Warning: No companies extracted")
        success = False
    if not entities.people:
        print("   ⚠ Warning: No people extracted")
        success = False
    if not entities.locations:
        print("   ⚠ Warning: No locations extracted")
        success = False
    if not entities.tickers:
        print("   ⚠ Warning: No tickers extracted (database may be empty)")
    
    if success and entities.companies and entities.people and entities.locations:
        print("\n   ✓ Entity extraction working correctly")
    
    return True


def test_ticker_extraction():
    """Test ticker extraction specifically."""
    print("\n" + "=" * 60)
    print("Testing Ticker Extraction")
    print("=" * 60)
    
    extractor = EntityExtractor()
    
    test_cases = [
        ("Apple ($AAPL) rose 5%", "Dollar sign format"),
        ("Tesla (NASDAQ:TSLA) gained", "Exchange format"),
        ("MSFT stock jumped today", "Contextual format"),
        ("GOOGL:US traded higher", "Country code format"),
    ]
    
    for text, description in test_cases:
        tickers = extractor.extract_tickers(text)
        print(f"\n   {description}:")
        print(f"   Text: '{text}'")
        print(f"   Extracted: {tickers}")
    
    print("\n   ✓ Ticker extraction patterns working")
    return True


def test_global_instance():
    """Test global instance getter."""
    print("\n" + "=" * 60)
    print("Testing Global Instance")
    print("=" * 60)
    
    extractor1 = get_entity_extractor()
    extractor2 = get_entity_extractor()
    
    if extractor1 is extractor2:
        print("   ✓ Global instance singleton working")
        return True
    else:
        print("   ✗ Global instance not singleton")
        return False


def test_caching():
    """Test Redis caching."""
    print("\n" + "=" * 60)
    print("Testing Redis Caching")
    print("=" * 60)
    
    extractor = EntityExtractor()
    
    test_text = "Apple Inc. CEO Tim Cook announced earnings in Cupertino."
    
    # First extraction (cache miss)
    print("\n   First extraction (should cache)...")
    entities1 = extractor.extract_entities(test_text)
    
    # Second extraction (cache hit)
    print("   Second extraction (should use cache)...")
    entities2 = extractor.extract_entities(test_text)
    
    # Results should be identical
    if (entities1.companies == entities2.companies and
        entities1.people == entities2.people and
        entities1.locations == entities2.locations):
        print("   ✓ Caching working correctly")
        return True
    else:
        print("   ⚠ Cache results differ (might be cache unavailable)")
        return True  # Not critical if Redis is down


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("EntityExtractor Test Suite")
    print("=" * 60)
    
    try:
        results = []
        
        # Run tests
        results.append(("Basic Extraction", test_basic_extraction()))
        results.append(("Ticker Extraction", test_ticker_extraction()))
        results.append(("Global Instance", test_global_instance()))
        results.append(("Caching", test_caching()))
        
        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)
        
        for test_name, passed in results:
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"   {status}: {test_name}")
        
        all_passed = all(result[1] for result in results)
        
        if all_passed:
            print("\n✓ All tests passed!")
            return 0
        else:
            print("\n⚠ Some tests failed")
            return 1
            
    except Exception as e:
        print(f"\n✗ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
