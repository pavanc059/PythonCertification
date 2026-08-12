"""
Feature Engineering Demo

This script demonstrates the usage of the feature engineering module
for stock analysis and ML pipeline integration.

Usage:
    python examples/feature_engineering_demo.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from stockiq.models.features import (
    create_feature_matrix,
    calculate_technical_features,
    calculate_fundamental_features,
    calculate_sentiment_features,
    create_feature_matrices,
)
import pandas as pd
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def demo_single_stock():
    """Demonstrate feature engineering for a single stock."""
    print("\n" + "="*80)
    print("DEMO 1: Feature Engineering for Single Stock")
    print("="*80)
    
    ticker = "AAPL"
    lookback_days = 90
    
    print(f"\nCreating feature matrix for {ticker} with {lookback_days} days of history...")
    
    try:
        # Create complete feature matrix
        features = create_feature_matrix(ticker, lookback_days=lookback_days)
        
        print(f"\n✓ Successfully created feature matrix")
        print(f"  - Shape: {features.shape[0]} rows × {features.shape[1]} columns")
        print(f"  - Date range: {features.index[0].date()} to {features.index[-1].date()}")
        
        # Display feature categories
        technical_features = [col for col in features.columns 
                            if not col.startswith(('fund_', 'sent_', 'target_'))]
        fundamental_features = [col for col in features.columns if col.startswith('fund_')]
        sentiment_features = [col for col in features.columns if col.startswith('sent_')]
        
        print(f"\n  Feature Breakdown:")
        print(f"  - Technical features: {len(technical_features)}")
        print(f"  - Fundamental features: {len(fundamental_features)}")
        print(f"  - Sentiment features: {len(sentiment_features)}")
        
        # Show sample of latest data
        print(f"\n  Latest data (last 3 rows):")
        display_cols = ['Close', 'rsi', 'macd', 'sma_20', 'bb_position', 'volume_ratio']
        print(features[display_cols].tail(3).to_string())
        
        # Check data quality
        missing_pct = (features.iloc[:-1].isna().sum().sum() / (features.iloc[:-1].size)) * 100
        print(f"\n  Data Quality:")
        print(f"  - Missing values: {missing_pct:.2f}%")
        
        return features
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return None


def demo_fundamental_features():
    """Demonstrate fundamental feature extraction."""
    print("\n" + "="*80)
    print("DEMO 2: Fundamental Feature Extraction")
    print("="*80)
    
    ticker = "MSFT"
    print(f"\nExtracting fundamental features for {ticker}...")
    
    try:
        features = calculate_fundamental_features(ticker)
        
        print(f"\n✓ Successfully extracted {len(features)} fundamental metrics")
        
        # Display key metrics
        key_metrics = ['pe_ratio', 'pb_ratio', 'debt_to_equity', 'roe', 
                      'profit_margin', 'beta', 'market_cap']
        
        print(f"\n  Key Metrics:")
        for metric in key_metrics:
            value = features.get(metric)
            if pd.notna(value):
                if metric == 'market_cap':
                    print(f"  - {metric}: ${value:,.0f}")
                elif metric in ['profit_margin', 'roe']:
                    print(f"  - {metric}: {value*100:.2f}%")
                else:
                    print(f"  - {metric}: {value:.2f}")
            else:
                print(f"  - {metric}: N/A")
        
        return features
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return None


def demo_batch_processing():
    """Demonstrate batch processing of multiple stocks."""
    print("\n" + "="*80)
    print("DEMO 3: Batch Feature Engineering")
    print("="*80)
    
    tickers = ["AAPL", "GOOGL", "MSFT", "AMZN"]
    lookback_days = 30
    
    print(f"\nProcessing {len(tickers)} stocks: {', '.join(tickers)}")
    print(f"Lookback period: {lookback_days} days\n")
    
    try:
        # Process multiple stocks
        features_dict = create_feature_matrices(tickers, lookback_days=lookback_days)
        
        print(f"\n✓ Successfully processed {len(features_dict)}/{len(tickers)} stocks")
        
        # Display summary for each stock
        print(f"\n  Summary by Stock:")
        for ticker, features in features_dict.items():
            latest_close = features['Close'].iloc[-1]
            sma_20 = features['sma_20'].iloc[-1]
            rsi = features['rsi'].iloc[-1]
            
            print(f"\n  {ticker}:")
            print(f"    - Latest Close: ${latest_close:.2f}")
            print(f"    - SMA(20): ${sma_20:.2f}")
            print(f"    - RSI: {rsi:.2f}")
            print(f"    - Feature count: {features.shape[1]} columns")
            print(f"    - Data points: {features.shape[0]} rows")
        
        return features_dict
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return None


def demo_ml_pipeline_integration():
    """Demonstrate integration with ML pipeline."""
    print("\n" + "="*80)
    print("DEMO 4: ML Pipeline Integration")
    print("="*80)
    
    ticker = "TSLA"
    print(f"\nPreparing features for ML model training ({ticker})...")
    
    try:
        # Create feature matrix
        features = create_feature_matrix(ticker, lookback_days=180)
        
        # Separate features and targets
        target_cols = ['target_return', 'target_direction']
        feature_cols = [col for col in features.columns if col not in target_cols]
        
        # Remove last row (no target available)
        X = features[feature_cols].iloc[:-1]
        y_return = features['target_return'].iloc[:-1]
        y_direction = features['target_direction'].iloc[:-1]
        
        print(f"\n✓ Feature matrix prepared for ML")
        print(f"  - Training samples: {len(X)}")
        print(f"  - Feature count: {len(feature_cols)}")
        print(f"  - Target variables: Return prediction, Direction classification")
        
        # Show target distribution
        positive_days = (y_direction == 1).sum()
        negative_days = (y_direction == 0).sum()
        
        print(f"\n  Target Distribution:")
        print(f"  - Positive days (price up): {positive_days} ({positive_days/len(y_direction)*100:.1f}%)")
        print(f"  - Negative days (price down): {negative_days} ({negative_days/len(y_direction)*100:.1f}%)")
        
        # Show feature statistics
        print(f"\n  Sample Feature Statistics:")
        sample_features = ['rsi', 'macd', 'volatility', 'volume_ratio']
        stats_df = X[sample_features].describe().loc[['mean', 'std', 'min', 'max']]
        print(stats_df.to_string())
        
        return X, y_return, y_direction
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return None, None, None


def main():
    """Run all demos."""
    print("\n" + "="*80)
    print("Feature Engineering Module - Demonstration")
    print("="*80)
    print("\nThis demo showcases the feature engineering capabilities of the")
    print("institutional-grade stock analyzer upgrade.")
    
    # Run demos
    demo_single_stock()
    demo_fundamental_features()
    demo_batch_processing()
    demo_ml_pipeline_integration()
    
    print("\n" + "="*80)
    print("Demo Complete!")
    print("="*80)
    print("\nThe feature engineering module is ready for integration with:")
    print("  - ML prediction models (LSTM, Transformers, Ensemble)")
    print("  - Backtesting engine")
    print("  - Real-time analysis pipeline")
    print("  - Paper trading system")
    print("\n")


if __name__ == "__main__":
    main()
