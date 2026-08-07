"""
Schema verification script.

This script verifies that all required database tables, indexes, and constraints
are properly defined and can be created successfully.
"""

import sys
import os

# Add parent directory to path to import stockiq
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateTable
import structlog

logger = structlog.get_logger(__name__)


def verify_model_definitions():
    """Verify that all ORM models are properly defined."""
    from stockiq.infrastructure.models import (
        Stock, PriceData, NewsArticle, NewsSentiment,
        DailyPrediction, TopMover, PennyStockMomentum,
        PennyStockRiskMetrics, Alert, UserWatchlist
    )
    
    required_models = [
        ("Stock", Stock),
        ("PriceData", PriceData),
        ("NewsArticle", NewsArticle),
        ("NewsSentiment", NewsSentiment),
        ("DailyPrediction", DailyPrediction),
        ("TopMover", TopMover),
        ("PennyStockMomentum", PennyStockMomentum),
        ("PennyStockRiskMetrics", PennyStockRiskMetrics),
        ("Alert", Alert),
        ("UserWatchlist", UserWatchlist),
    ]
    
    logger.info("verifying_model_definitions")
    
    for name, model in required_models:
        # Check table name
        if not hasattr(model, '__tablename__'):
            logger.error("model_missing_tablename", model=name)
            return False
        
        # Check columns
        if not hasattr(model, '__table__'):
            logger.error("model_missing_table", model=name)
            return False
        
        columns = model.__table__.columns
        if len(columns) == 0:
            logger.error("model_has_no_columns", model=name)
            return False
        
        logger.info("model_verified", model=name, table=model.__tablename__, columns=len(columns))
    
    logger.info("all_models_verified", count=len(required_models))
    return True


def verify_required_fields():
    """Verify that required fields exist in each model."""
    from stockiq.infrastructure.models import (
        Stock, PriceData, NewsArticle, NewsSentiment,
        DailyPrediction, TopMover, PennyStockMomentum,
        PennyStockRiskMetrics
    )
    
    logger.info("verifying_required_fields")
    
    # Verify Stock table
    stock_columns = [c.name for c in Stock.__table__.columns]
    required_stock_fields = ['ticker', 'name', 'sector', 'market_cap', 'avg_volume']
    for field in required_stock_fields:
        if field not in stock_columns:
            logger.error("missing_required_field", model="Stock", field=field)
            return False
    logger.info("stock_fields_verified", fields=required_stock_fields)
    
    # Verify PriceData table
    price_columns = [c.name for c in PriceData.__table__.columns]
    required_price_fields = ['stock_id', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
    for field in required_price_fields:
        if field not in price_columns:
            logger.error("missing_required_field", model="PriceData", field=field)
            return False
    logger.info("price_data_fields_verified", fields=required_price_fields)
    
    # Verify NewsArticle table
    news_columns = [c.name for c in NewsArticle.__table__.columns]
    required_news_fields = ['article_id', 'title', 'content', 'source', 'published_at', 'url', 'category']
    for field in required_news_fields:
        if field not in news_columns:
            logger.error("missing_required_field", model="NewsArticle", field=field)
            return False
    logger.info("news_article_fields_verified", fields=required_news_fields)
    
    # Verify NewsSentiment table
    sentiment_columns = [c.name for c in NewsSentiment.__table__.columns]
    required_sentiment_fields = ['article_id', 'stock_id', 'sentiment_score', 'vader_score', 'finbert_score']
    for field in required_sentiment_fields:
        if field not in sentiment_columns:
            logger.error("missing_required_field", model="NewsSentiment", field=field)
            return False
    logger.info("news_sentiment_fields_verified", fields=required_sentiment_fields)
    
    # Verify DailyPrediction table
    prediction_columns = [c.name for c in DailyPrediction.__table__.columns]
    required_prediction_fields = ['stock_id', 'prediction_date', 'predicted_price', 'confidence', 'factors']
    for field in required_prediction_fields:
        if field not in prediction_columns:
            logger.error("missing_required_field", model="DailyPrediction", field=field)
            return False
    logger.info("daily_prediction_fields_verified", fields=required_prediction_fields)
    
    # Verify TopMover table
    mover_columns = [c.name for c in TopMover.__table__.columns]
    required_mover_fields = ['stock_id', 'date', 'price_change_pct', 'volume_ratio']
    for field in required_mover_fields:
        if field not in mover_columns:
            logger.error("missing_required_field", model="TopMover", field=field)
            return False
    logger.info("top_mover_fields_verified", fields=required_mover_fields)
    
    # Verify PennyStockMomentum table
    momentum_columns = [c.name for c in PennyStockMomentum.__table__.columns]
    required_momentum_fields = ['ticker', 'date', 'momentum_score', 'price_change_pct', 'volume_ratio']
    for field in required_momentum_fields:
        if field not in momentum_columns:
            logger.error("missing_required_field", model="PennyStockMomentum", field=field)
            return False
    logger.info("penny_stock_momentum_fields_verified", fields=required_momentum_fields)
    
    # Verify PennyStockRiskMetrics table
    risk_columns = [c.name for c in PennyStockRiskMetrics.__table__.columns]
    required_risk_fields = ['ticker', 'date', 'liquidity_risk', 'volatility_risk', 'spread_percentage']
    for field in required_risk_fields:
        if field not in risk_columns:
            logger.error("missing_required_field", model="PennyStockRiskMetrics", field=field)
            return False
    logger.info("penny_stock_risk_fields_verified", fields=required_risk_fields)
    
    logger.info("all_required_fields_verified")
    return True


def verify_indexes():
    """Verify that required indexes are defined."""
    from stockiq.infrastructure.models import (
        Stock, PriceData, NewsArticle, NewsSentiment,
        DailyPrediction, TopMover, PennyStockMomentum,
        PennyStockRiskMetrics
    )
    
    logger.info("verifying_indexes")
    
    models_to_check = [
        ("Stock", Stock, ['ticker']),
        ("PriceData", PriceData, ['stock_id', 'timestamp']),
        ("NewsArticle", NewsArticle, ['article_id', 'published_at', 'category']),
        ("NewsSentiment", NewsSentiment, ['article_id', 'stock_id']),
        ("DailyPrediction", DailyPrediction, ['stock_id', 'prediction_date']),
        ("TopMover", TopMover, ['date', 'is_gainer']),
        ("PennyStockMomentum", PennyStockMomentum, ['ticker', 'date']),
        ("PennyStockRiskMetrics", PennyStockRiskMetrics, ['ticker', 'date']),
    ]
    
    for model_name, model, expected_indexed_columns in models_to_check:
        # Get all indexes from the table
        indexes = model.__table__.indexes
        index_columns = set()
        
        for index in indexes:
            for col in index.columns:
                index_columns.add(col.name)
        
        # Check if expected columns are indexed
        missing_indexes = []
        for col in expected_indexed_columns:
            if col not in index_columns:
                # Some columns might be indexed as part of unique constraints
                column_obj = model.__table__.columns.get(col)
                if column_obj and not (column_obj.primary_key or column_obj.unique or column_obj.index):
                    missing_indexes.append(col)
        
        if missing_indexes:
            logger.warning("missing_indexes", model=model_name, columns=missing_indexes)
        else:
            logger.info("indexes_verified", model=model_name)
    
    logger.info("index_verification_completed")
    return True


def verify_constraints():
    """Verify that check constraints are properly defined."""
    from stockiq.infrastructure.models import (
        PriceData, NewsSentiment, DailyPrediction,
        PennyStockMomentum, PennyStockRiskMetrics
    )
    
    logger.info("verifying_constraints")
    
    # Verify PriceData constraints
    price_constraints = [c.name for c in PriceData.__table__.constraints if hasattr(c, 'name')]
    expected_price_constraints = [
        'check_high_gte_open', 'check_high_gte_close',
        'check_low_lte_open', 'check_low_lte_close',
        'check_volume_non_negative'
    ]
    for constraint in expected_price_constraints:
        if constraint in price_constraints:
            logger.info("constraint_verified", model="PriceData", constraint=constraint)
        else:
            logger.warning("constraint_not_found", model="PriceData", constraint=constraint)
    
    # Verify NewsSentiment constraints
    sentiment_constraints = [c.name for c in NewsSentiment.__table__.constraints if hasattr(c, 'name')]
    if 'check_sentiment_range' in sentiment_constraints:
        logger.info("constraint_verified", model="NewsSentiment", constraint="check_sentiment_range")
    else:
        logger.warning("constraint_not_found", model="NewsSentiment", constraint="check_sentiment_range")
    
    # Verify DailyPrediction constraints
    prediction_constraints = [c.name for c in DailyPrediction.__table__.constraints if hasattr(c, 'name')]
    expected_prediction_constraints = [
        'check_confidence_range', 'check_lower_bound', 'check_upper_bound'
    ]
    for constraint in expected_prediction_constraints:
        if constraint in prediction_constraints:
            logger.info("constraint_verified", model="DailyPrediction", constraint=constraint)
        else:
            logger.warning("constraint_not_found", model="DailyPrediction", constraint=constraint)
    
    # Verify PennyStockMomentum constraints
    momentum_constraints = [c.name for c in PennyStockMomentum.__table__.constraints if hasattr(c, 'name')]
    expected_momentum_constraints = [
        'check_penny_price', 'check_momentum_range', 'check_volume_ratio'
    ]
    for constraint in expected_momentum_constraints:
        if constraint in momentum_constraints:
            logger.info("constraint_verified", model="PennyStockMomentum", constraint=constraint)
        else:
            logger.warning("constraint_not_found", model="PennyStockMomentum", constraint=constraint)
    
    # Verify PennyStockRiskMetrics constraints
    risk_constraints = [c.name for c in PennyStockRiskMetrics.__table__.constraints if hasattr(c, 'name')]
    expected_risk_constraints = [
        'check_liquidity_risk_range', 'check_volatility_risk_range',
        'check_spread_non_negative'
    ]
    for constraint in expected_risk_constraints:
        if constraint in risk_constraints:
            logger.info("constraint_verified", model="PennyStockRiskMetrics", constraint=constraint)
        else:
            logger.warning("constraint_not_found", model="PennyStockRiskMetrics", constraint=constraint)
    
    logger.info("constraint_verification_completed")
    return True


def verify_relationships():
    """Verify that foreign key relationships are properly defined."""
    from sqlalchemy.orm import class_mapper
    from stockiq.infrastructure.models import (
        Stock, PriceData, NewsArticle, NewsSentiment,
        DailyPrediction, TopMover
    )
    
    logger.info("verifying_relationships")
    
    # Verify Stock relationships
    stock_mapper = class_mapper(Stock)
    stock_relationships = [rel.key for rel in stock_mapper.relationships]
    expected_stock_rels = ['price_data', 'news_sentiment', 'predictions', 'top_movers']
    for rel in expected_stock_rels:
        if rel in stock_relationships:
            logger.info("relationship_verified", model="Stock", relationship=rel)
        else:
            logger.warning("relationship_not_found", model="Stock", relationship=rel)
    
    # Verify PriceData relationships
    price_mapper = class_mapper(PriceData)
    price_relationships = [rel.key for rel in price_mapper.relationships]
    if 'stock' in price_relationships:
        logger.info("relationship_verified", model="PriceData", relationship="stock")
    else:
        logger.warning("relationship_not_found", model="PriceData", relationship="stock")
    
    # Verify NewsArticle relationships
    news_mapper = class_mapper(NewsArticle)
    news_relationships = [rel.key for rel in news_mapper.relationships]
    if 'sentiment' in news_relationships:
        logger.info("relationship_verified", model="NewsArticle", relationship="sentiment")
    else:
        logger.warning("relationship_not_found", model="NewsArticle", relationship="sentiment")
    
    # Verify NewsSentiment relationships
    sentiment_mapper = class_mapper(NewsSentiment)
    sentiment_relationships = [rel.key for rel in sentiment_mapper.relationships]
    expected_sentiment_rels = ['article', 'stock']
    for rel in expected_sentiment_rels:
        if rel in sentiment_relationships:
            logger.info("relationship_verified", model="NewsSentiment", relationship=rel)
        else:
            logger.warning("relationship_not_found", model="NewsSentiment", relationship=rel)
    
    logger.info("relationship_verification_completed")
    return True


def print_create_table_statements():
    """Print CREATE TABLE statements for all models."""
    from stockiq.infrastructure.models import Base
    from stockiq.infrastructure.database import get_engine
    
    logger.info("generating_create_table_statements")
    
    engine = get_engine()
    
    print("\n" + "="*80)
    print("CREATE TABLE STATEMENTS")
    print("="*80 + "\n")
    
    for table in Base.metadata.sorted_tables:
        print(f"-- {table.name}")
        print(CreateTable(table).compile(engine))
        print("\n")
    
    logger.info("create_table_statements_generated")


def main():
    """Main verification function."""
    logger.info("starting_schema_verification")
    
    print("\n" + "="*80)
    print("DATABASE SCHEMA VERIFICATION")
    print("="*80 + "\n")
    
    all_passed = True
    
    # Step 1: Verify model definitions
    print("1. Verifying model definitions...")
    if not verify_model_definitions():
        print("   ❌ Model definition verification FAILED")
        all_passed = False
    else:
        print("   ✅ Model definitions verified")
    
    # Step 2: Verify required fields
    print("\n2. Verifying required fields...")
    if not verify_required_fields():
        print("   ❌ Required fields verification FAILED")
        all_passed = False
    else:
        print("   ✅ Required fields verified")
    
    # Step 3: Verify indexes
    print("\n3. Verifying indexes...")
    if not verify_indexes():
        print("   ❌ Index verification FAILED")
        all_passed = False
    else:
        print("   ✅ Indexes verified")
    
    # Step 4: Verify constraints
    print("\n4. Verifying constraints...")
    if not verify_constraints():
        print("   ❌ Constraint verification FAILED")
        all_passed = False
    else:
        print("   ✅ Constraints verified")
    
    # Step 5: Verify relationships
    print("\n5. Verifying relationships...")
    if not verify_relationships():
        print("   ❌ Relationship verification FAILED")
        all_passed = False
    else:
        print("   ✅ Relationships verified")
    
    # Step 6: Print CREATE TABLE statements
    print("\n6. Generating CREATE TABLE statements...")
    try:
        print_create_table_statements()
        print("   ✅ CREATE TABLE statements generated")
    except Exception as e:
        print(f"   ❌ Failed to generate CREATE TABLE statements: {e}")
        all_passed = False
    
    # Final result
    print("\n" + "="*80)
    if all_passed:
        print("✅ SCHEMA VERIFICATION PASSED")
        print("\nThe database schema is properly defined and ready to be created.")
        print("\nNext steps:")
        print("1. Ensure PostgreSQL with TimescaleDB is running")
        print("2. Run 'python scripts/init_db.py' to create the schema")
        print("3. Verify creation with 'psql -d stockiq -c \"\\dt\"'")
    else:
        print("❌ SCHEMA VERIFICATION FAILED")
        print("\nSome verifications failed. Check the logs above for details.")
        sys.exit(1)
    print("="*80 + "\n")
    
    logger.info("schema_verification_completed", passed=all_passed)


if __name__ == "__main__":
    main()
