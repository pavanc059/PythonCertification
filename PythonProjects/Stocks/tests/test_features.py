"""
Unit tests for the feature engineering module.

Tests cover:
- Technical indicator calculations (RSI, MACD, Bollinger Bands, ATR, OBV)
- Moving average calculations
- Momentum indicators
- Fundamental feature extraction
- Sentiment features (placeholder)
- Complete feature matrix creation
"""

import pytest
import pandas as pd
import numpy as np
from stockiq.models.features import (
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_obv,
    calculate_technical_features,
    calculate_fundamental_features,
    calculate_sentiment_features,
    create_feature_matrix,
)


class TestTechnicalIndicators:
    """Test individual technical indicator calculations."""
    
    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data for testing."""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=100, freq='D')
        
        # Generate synthetic price data with trend
        base_price = 100
        trend = np.linspace(0, 20, 100)
        noise = np.random.randn(100) * 2
        close_prices = base_price + trend + noise
        
        data = pd.DataFrame({
            'Open': close_prices * 0.99,
            'High': close_prices * 1.02,
            'Low': close_prices * 0.98,
            'Close': close_prices,
            'Volume': np.random.randint(1000000, 5000000, 100)
        }, index=dates)
        
        return data
    
    def test_calculate_rsi_basic(self, sample_price_data):
        """Test RSI calculation returns values in valid range."""
        rsi = calculate_rsi(sample_price_data['Close'])
        
        # RSI should be between 0 and 100
        assert rsi.min() >= 0
        assert rsi.max() <= 100
        
        # RSI should have NaN values at the start (warm-up period)
        assert rsi.isna().sum() > 0
        assert rsi.isna().sum() < len(rsi)
    
    def test_calculate_rsi_custom_period(self, sample_price_data):
        """Test RSI with custom period."""
        rsi_14 = calculate_rsi(sample_price_data['Close'], period=14)
        rsi_7 = calculate_rsi(sample_price_data['Close'], period=7)
        
        # Shorter period should have fewer NaN values
        assert rsi_7.isna().sum() < rsi_14.isna().sum()
    
    def test_calculate_macd(self, sample_price_data):
        """Test MACD calculation."""
        macd_data = calculate_macd(sample_price_data['Close'])
        
        # Check all components are present
        assert 'macd' in macd_data
        assert 'macd_signal' in macd_data
        assert 'macd_histogram' in macd_data
        
        # Check lengths match
        assert len(macd_data['macd']) == len(sample_price_data)
        assert len(macd_data['macd_signal']) == len(sample_price_data)
        assert len(macd_data['macd_histogram']) == len(sample_price_data)
        
        # Histogram should equal MACD - Signal
        diff = macd_data['macd'] - macd_data['macd_signal'] - macd_data['macd_histogram']
        assert np.allclose(diff.dropna(), 0, atol=1e-10)
    
    def test_calculate_bollinger_bands(self, sample_price_data):
        """Test Bollinger Bands calculation."""
        bb_data = calculate_bollinger_bands(sample_price_data['Close'])
        
        # Check all components are present
        assert 'bb_upper' in bb_data
        assert 'bb_middle' in bb_data
        assert 'bb_lower' in bb_data
        assert 'bb_width' in bb_data
        
        # Upper band should always be above lower band
        valid_idx = ~bb_data['bb_upper'].isna()
        assert (bb_data['bb_upper'][valid_idx] >= bb_data['bb_lower'][valid_idx]).all()
        
        # Middle band should be between upper and lower
        assert (bb_data['bb_middle'][valid_idx] >= bb_data['bb_lower'][valid_idx]).all()
        assert (bb_data['bb_middle'][valid_idx] <= bb_data['bb_upper'][valid_idx]).all()
    
    def test_calculate_atr(self, sample_price_data):
        """Test ATR calculation."""
        atr = calculate_atr(
            sample_price_data['High'],
            sample_price_data['Low'],
            sample_price_data['Close']
        )
        
        # ATR should be positive
        assert (atr.dropna() > 0).all()
        
        # ATR should have expected length
        assert len(atr) == len(sample_price_data)
    
    def test_calculate_obv(self, sample_price_data):
        """Test OBV calculation."""
        obv = calculate_obv(sample_price_data['Close'], sample_price_data['Volume'])
        
        # OBV should have no NaN values
        assert obv.isna().sum() == 0
        
        # OBV should have expected length
        assert len(obv) == len(sample_price_data)
        
        # First OBV value should equal first volume
        assert obv.iloc[0] == sample_price_data['Volume'].iloc[0]


class TestTechnicalFeatures:
    """Test the complete technical features function."""
    
    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data for testing."""
        np.random.seed(42)
        dates = pd.date_range('2023-01-01', periods=250, freq='D')
        
        base_price = 100
        trend = np.linspace(0, 50, 250)
        noise = np.random.randn(250) * 3
        close_prices = base_price + trend + noise
        
        data = pd.DataFrame({
            'Open': close_prices * 0.99,
            'High': close_prices * 1.03,
            'Low': close_prices * 0.97,
            'Close': close_prices,
            'Volume': np.random.randint(1000000, 10000000, 250)
        }, index=dates)
        
        return data
    
    def test_calculate_technical_features_columns(self, sample_price_data):
        """Test that all expected technical features are calculated."""
        result = calculate_technical_features(sample_price_data)
        
        # Check that result has more columns than input
        assert len(result.columns) > len(sample_price_data.columns)
        
        # Check for key technical indicators
        expected_features = [
            'rsi', 'macd', 'macd_signal', 'macd_histogram',
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
            'atr', 'obv',
            'sma_20', 'sma_50', 'sma_200',
            'ema_12', 'ema_26',
            'momentum', 'rate_of_change',
            'price_to_sma20', 'price_to_sma50', 'price_to_sma200',
            'bb_position', 'volume_sma_20', 'volume_ratio',
            'volatility', 'daily_return', 'price_range', 'price_range_pct'
        ]
        
        for feature in expected_features:
            assert feature in result.columns, f"Missing feature: {feature}"
    
    def test_calculate_technical_features_shape(self, sample_price_data):
        """Test that output has correct shape."""
        result = calculate_technical_features(sample_price_data)
        
        # Same number of rows
        assert len(result) == len(sample_price_data)
        
        # More columns
        assert len(result.columns) > len(sample_price_data.columns)
    
    def test_calculate_technical_features_missing_columns(self):
        """Test error handling for missing required columns."""
        incomplete_data = pd.DataFrame({
            'Close': [100, 101, 102],
            'Volume': [1000, 1100, 1200]
        })
        
        with pytest.raises(ValueError, match="Missing required columns"):
            calculate_technical_features(incomplete_data)
    
    def test_calculate_technical_features_preserves_original(self, sample_price_data):
        """Test that original columns are preserved."""
        result = calculate_technical_features(sample_price_data)
        
        for col in sample_price_data.columns:
            assert col in result.columns
            # Original data should be unchanged
            pd.testing.assert_series_equal(
                result[col], 
                sample_price_data[col],
                check_names=True
            )


class TestFundamentalFeatures:
    """Test fundamental feature extraction."""
    
    def test_calculate_fundamental_features_returns_dict(self):
        """Test that function returns a dictionary."""
        features = calculate_fundamental_features('AAPL')
        assert isinstance(features, dict)
    
    def test_calculate_fundamental_features_has_expected_keys(self):
        """Test that expected fundamental metrics are present."""
        features = calculate_fundamental_features('AAPL')
        
        expected_keys = [
            'pe_ratio', 'pb_ratio', 'debt_to_equity', 'roe',
            'profit_margin', 'market_cap', 'beta'
        ]
        
        for key in expected_keys:
            assert key in features, f"Missing key: {key}"
    
    def test_calculate_fundamental_features_invalid_ticker(self):
        """Test error handling for invalid ticker."""
        features = calculate_fundamental_features('INVALID_TICKER_12345')
        
        # Should return dict with NaN values instead of raising error
        assert isinstance(features, dict)
        # Most values should be NaN for invalid ticker
        nan_count = sum(1 for v in features.values() if pd.isna(v))
        assert nan_count > 0


class TestSentimentFeatures:
    """Test sentiment feature calculation (placeholder)."""
    
    def test_calculate_sentiment_features_returns_dict(self):
        """Test that function returns a dictionary."""
        features = calculate_sentiment_features('AAPL')
        assert isinstance(features, dict)
    
    def test_calculate_sentiment_features_has_expected_keys(self):
        """Test that expected sentiment metrics are present."""
        features = calculate_sentiment_features('AAPL')
        
        expected_keys = [
            'average_sentiment', 'sentiment_trend', 'news_volume',
            'positive_ratio', 'negative_ratio'
        ]
        
        for key in expected_keys:
            assert key in features, f"Missing key: {key}"
    
    def test_calculate_sentiment_features_placeholder_values(self):
        """Test that placeholder returns neutral values."""
        features = calculate_sentiment_features('AAPL')
        
        # Placeholder should return neutral/zero values
        assert features['average_sentiment'] == 0.0
        assert features['sentiment_trend'] == 0.0
        assert features['news_volume'] == 0


class TestFeatureMatrix:
    """Test complete feature matrix creation."""
    
    @pytest.mark.slow
    def test_create_feature_matrix_shape(self):
        """Test that feature matrix has expected shape."""
        # This test makes real API calls, so mark as slow
        df = create_feature_matrix('AAPL', lookback_days=30)
        
        # Should have approximately 30 rows (may vary due to trading days)
        assert 20 <= len(df) <= 35
        
        # Should have many columns (technical + fundamental + sentiment)
        assert len(df.columns) > 40
    
    @pytest.mark.slow
    def test_create_feature_matrix_has_all_feature_types(self):
        """Test that feature matrix includes all feature types."""
        df = create_feature_matrix('AAPL', lookback_days=30)
        
        # Check for technical features
        assert 'rsi' in df.columns
        assert 'macd' in df.columns
        
        # Check for fundamental features (prefixed with 'fund_')
        fund_cols = [col for col in df.columns if col.startswith('fund_')]
        assert len(fund_cols) > 0
        
        # Check for sentiment features (prefixed with 'sent_')
        sent_cols = [col for col in df.columns if col.startswith('sent_')]
        assert len(sent_cols) > 0
    
    @pytest.mark.slow
    def test_create_feature_matrix_handles_missing_values(self):
        """Test that missing values are handled appropriately."""
        df = create_feature_matrix('AAPL', lookback_days=30)
        
        # Most recent rows should have minimal NaN values
        # (only the target variables at the very end should be NaN)
        recent_data = df.iloc[-5:-1]  # Exclude last row with NaN target
        nan_percentage = (recent_data.isna().sum().sum() / recent_data.size) * 100
        
        # Should have very few NaN values (< 5%)
        assert nan_percentage < 5.0
    
    def test_create_feature_matrix_invalid_ticker(self):
        """Test error handling for invalid ticker."""
        with pytest.raises(ValueError):
            create_feature_matrix('INVALID_TICKER_12345', lookback_days=30)


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_rsi_with_constant_prices(self):
        """Test RSI when prices don't change."""
        constant_prices = pd.Series([100.0] * 50)
        rsi = calculate_rsi(constant_prices)
        
        # RSI should be NaN or 50 for constant prices
        assert rsi.isna().all() or np.allclose(rsi.dropna(), 50, atol=1)
    
    def test_obv_with_zero_volume(self):
        """Test OBV with zero volume edge case."""
        prices = pd.Series([100, 101, 102, 103, 104])
        volumes = pd.Series([1000, 0, 1000, 0, 1000])
        
        obv = calculate_obv(prices, volumes)
        
        # Should handle zero volume without errors
        assert len(obv) == len(prices)
        assert not obv.isna().any()
    
    def test_bollinger_bands_with_low_volatility(self):
        """Test Bollinger Bands with very low volatility."""
        # Prices with minimal variation
        low_vol_prices = pd.Series([100.0, 100.01, 100.02, 100.01, 100.0] * 10)
        bb_data = calculate_bollinger_bands(low_vol_prices)
        
        # Bands should be very narrow
        valid_idx = ~bb_data['bb_width'].isna()
        assert (bb_data['bb_width'][valid_idx] < 1.0).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
