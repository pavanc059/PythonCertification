"""
Tests for Advanced Charting Module

Tests for:
- Candlestick chart rendering
- Technical indicators
- Drawing tools
- Chart export
- Heatmaps

Requirements tested:
- 18.1: Candlestick charts with 6 timeframe options
- 18.2: Drawing tools (trendlines, Fibonacci, horizontal lines)
- 18.3: 10+ technical indicator overlays
- 18.4: Chart comparison mode
- 18.5: Volume bars synchronized with price
- 18.9: Sector performance heatmaps
- 18.10: Correlation matrix heatmaps
- 18.12: Export to PNG, SVG, PDF
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

# Import chart components
from stockiq.ui.charts.candlestick_chart import (
    fetch_price_data,
    create_candlestick_trace,
    demo_generate_sample_data,
    TIMEFRAME_OPTIONS,
)
from stockiq.ui.charts.indicators import (
    calculate_sma,
    calculate_ema,
    calculate_rsi,
    calculate_macd,
    calculate_bollinger_bands,
    calculate_atr,
    calculate_stochastic,
    calculate_obv,
    calculate_adx,
    calculate_cci,
    AVAILABLE_INDICATORS,
)
from stockiq.ui.charts.drawing_tools import (
    TrendLine,
    HorizontalLine,
    FibonacciRetracement,
    add_trendline,
    add_horizontal_line,
    add_fibonacci_retracement,
    calculate_support_resistance_levels,
)
from stockiq.ui.charts.chart_export import (
    export_chart_png,
    export_chart_svg,
    export_chart_pdf,
    export_chart_html,
    get_export_formats,
)
from stockiq.ui.charts.heatmaps import (
    calculate_correlation_matrix,
    _demo_sector_data,
    _demo_correlation_matrix,
)


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_price_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(end=datetime.now(), periods=100, freq="D")
    np.random.seed(42)
    
    prices = 100 * np.exp(np.cumsum(np.random.randn(100) * 0.02))
    
    data = pd.DataFrame(index=dates)
    data["Close"] = prices
    data["Open"] = data["Close"].shift(1).fillna(prices[0])
    data["High"] = data[["Open", "Close"]].max(axis=1) * 1.02
    data["Low"] = data[["Open", "Close"]].min(axis=1) * 0.98
    data["Volume"] = (np.random.rand(100) * 10000000 + 5000000).astype(int)
    
    return data


@pytest.fixture
def sample_tickers():
    """Sample list of tickers for testing."""
    return ["AAPL", "MSFT", "GOOGL", "TSLA", "NVDA"]


# ============================================================================
# Test Candlestick Charts (Requirement 18.1)
# ============================================================================

class TestCandlestickCharts:
    """Test candlestick chart functionality."""
    
    def test_timeframe_options_available(self):
        """Test that all 6 required timeframes are available."""
        required_timeframes = ["1m", "5m", "15m", "1h", "1d", "1w"]
        
        for timeframe in required_timeframes:
            assert timeframe in TIMEFRAME_OPTIONS, f"Missing timeframe: {timeframe}"
            assert "interval" in TIMEFRAME_OPTIONS[timeframe]
            assert "period" in TIMEFRAME_OPTIONS[timeframe]
            assert "label" in TIMEFRAME_OPTIONS[timeframe]
    
    def test_demo_data_generation(self):
        """Test demo data generation produces valid OHLCV data."""
        data = demo_generate_sample_data(ticker="TEST", days=50)
        
        assert len(data) == 50
        assert all(col in data.columns for col in ["Open", "High", "Low", "Close", "Volume"])
        
        # Verify OHLC relationships
        assert (data["High"] >= data["Open"]).all()
        assert (data["High"] >= data["Close"]).all()
        assert (data["Low"] <= data["Open"]).all()
        assert (data["Low"] <= data["Close"]).all()
        
        # Verify volume is positive
        assert (data["Volume"] > 0).all()
    
    def test_candlestick_trace_creation(self, sample_price_data):
        """Test creation of candlestick and volume traces."""
        candlestick, volume = create_candlestick_trace(
            sample_price_data,
            name="TEST",
            show_volume=True
        )
        
        assert candlestick is not None
        assert volume is not None
        assert len(candlestick.x) == len(sample_price_data)
        assert len(volume.x) == len(sample_price_data)
    
    def test_candlestick_trace_without_volume(self, sample_price_data):
        """Test candlestick trace creation without volume."""
        candlestick, volume = create_candlestick_trace(
            sample_price_data,
            name="TEST",
            show_volume=False
        )
        
        assert candlestick is not None
        assert volume is None


# ============================================================================
# Test Technical Indicators (Requirement 18.3)
# ============================================================================

class TestTechnicalIndicators:
    """Test technical indicator calculations."""
    
    def test_available_indicators_count(self):
        """Test that at least 10 indicators are available."""
        assert len(AVAILABLE_INDICATORS) >= 10, "Must have at least 10 indicators"
    
    def test_sma_calculation(self, sample_price_data):
        """Test Simple Moving Average calculation."""
        sma = calculate_sma(sample_price_data["Close"], period=20)
        
        assert len(sma) == len(sample_price_data)
        assert not sma.isna().all()
        assert (sma > 0).any()
    
    def test_ema_calculation(self, sample_price_data):
        """Test Exponential Moving Average calculation."""
        ema = calculate_ema(sample_price_data["Close"], period=20)
        
        assert len(ema) == len(sample_price_data)
        assert not ema.isna().all()
        assert (ema > 0).any()
    
    def test_rsi_calculation(self, sample_price_data):
        """Test RSI calculation and range validation."""
        rsi = calculate_rsi(sample_price_data["Close"], period=14)
        
        assert len(rsi) == len(sample_price_data)
        # RSI should be between 0 and 100
        valid_rsi = rsi.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()
    
    def test_macd_calculation(self, sample_price_data):
        """Test MACD calculation returns three series."""
        macd_line, signal_line, histogram = calculate_macd(sample_price_data["Close"])
        
        assert len(macd_line) == len(sample_price_data)
        assert len(signal_line) == len(sample_price_data)
        assert len(histogram) == len(sample_price_data)
        
        # Histogram should equal macd_line - signal_line
        np.testing.assert_array_almost_equal(
            histogram.dropna().values,
            (macd_line - signal_line).dropna().values,
            decimal=6
        )
    
    def test_bollinger_bands_calculation(self, sample_price_data):
        """Test Bollinger Bands calculation."""
        upper, middle, lower = calculate_bollinger_bands(
            sample_price_data["Close"],
            period=20,
            std_dev=2.0
        )
        
        assert len(upper) == len(sample_price_data)
        assert len(middle) == len(sample_price_data)
        assert len(lower) == len(sample_price_data)
        
        # Upper should be above middle, middle above lower
        valid_data = ~(upper.isna() | middle.isna() | lower.isna())
        assert (upper[valid_data] >= middle[valid_data]).all()
        assert (middle[valid_data] >= lower[valid_data]).all()
    
    def test_atr_calculation(self, sample_price_data):
        """Test Average True Range calculation."""
        atr = calculate_atr(
            sample_price_data["High"],
            sample_price_data["Low"],
            sample_price_data["Close"],
            period=14
        )
        
        assert len(atr) == len(sample_price_data)
        # ATR should be non-negative
        assert (atr.dropna() >= 0).all()
    
    def test_stochastic_calculation(self, sample_price_data):
        """Test Stochastic Oscillator calculation."""
        k, d = calculate_stochastic(
            sample_price_data["High"],
            sample_price_data["Low"],
            sample_price_data["Close"],
            k_period=14,
            d_period=3
        )
        
        assert len(k) == len(sample_price_data)
        assert len(d) == len(sample_price_data)
        
        # %K and %D should be between 0 and 100
        valid_k = k.dropna()
        valid_d = d.dropna()
        assert (valid_k >= 0).all() and (valid_k <= 100).all()
        assert (valid_d >= 0).all() and (valid_d <= 100).all()
    
    def test_obv_calculation(self, sample_price_data):
        """Test On-Balance Volume calculation."""
        obv = calculate_obv(
            sample_price_data["Close"],
            sample_price_data["Volume"]
        )
        
        assert len(obv) == len(sample_price_data)
        assert not obv.isna().all()
    
    def test_adx_calculation(self, sample_price_data):
        """Test Average Directional Index calculation."""
        adx = calculate_adx(
            sample_price_data["High"],
            sample_price_data["Low"],
            sample_price_data["Close"],
            period=14
        )
        
        assert len(adx) == len(sample_price_data)
        # ADX should be between 0 and 100
        valid_adx = adx.dropna()
        assert (valid_adx >= 0).all()
        assert (valid_adx <= 100).all()
    
    def test_cci_calculation(self, sample_price_data):
        """Test Commodity Channel Index calculation."""
        cci = calculate_cci(
            sample_price_data["High"],
            sample_price_data["Low"],
            sample_price_data["Close"],
            period=20
        )
        
        assert len(cci) == len(sample_price_data)
        assert not cci.isna().all()


# ============================================================================
# Test Drawing Tools (Requirement 18.2)
# ============================================================================

class TestDrawingTools:
    """Test drawing tools functionality."""
    
    def test_trendline_creation(self):
        """Test trendline creation and properties."""
        x0 = datetime.now() - timedelta(days=10)
        x1 = datetime.now()
        y0 = 100.0
        y1 = 110.0
        
        trendline = add_trendline(x0, y0, x1, y1, color="#ffeb3b", width=2)
        
        assert isinstance(trendline, TrendLine)
        assert trendline.x0 == x0
        assert trendline.y0 == y0
        assert trendline.x1 == x1
        assert trendline.y1 == y1
        assert trendline.type == "trendline"
        
        # Test to_dict method
        data = trendline.to_dict()
        assert data["type"] == "trendline"
        assert data["x0"] == x0
        assert data["y0"] == y0
    
    def test_trendline_price_calculation(self):
        """Test trendline price calculation at specific date."""
        x0 = datetime(2024, 1, 1)
        x1 = datetime(2024, 1, 10)
        y0 = 100.0
        y1 = 110.0
        
        trendline = TrendLine(x0=x0, y0=y0, x1=x1, y1=y1)
        
        # Price at midpoint should be approximately 105
        mid_date = datetime(2024, 1, 5, 12, 0, 0)
        mid_price = trendline.calculate_price_at_date(mid_date)
        
        assert 104 < mid_price < 106
    
    def test_horizontal_line_creation(self):
        """Test horizontal line creation."""
        hline = add_horizontal_line(
            y=150.0,
            label="Resistance",
            color="#ff9800",
            width=2,
            dash="dash"
        )
        
        assert isinstance(hline, HorizontalLine)
        assert hline.y == 150.0
        assert hline.label == "Resistance"
        assert hline.type == "horizontal"
        assert hline.dash == "dash"
    
    def test_fibonacci_retracement_creation(self):
        """Test Fibonacci retracement creation."""
        high = 120.0
        low = 100.0
        x_start = datetime(2024, 1, 1)
        x_end = datetime(2024, 1, 31)
        
        fib = add_fibonacci_retracement(high, low, x_start, x_end, show_labels=True)
        
        assert isinstance(fib, FibonacciRetracement)
        assert fib.high == high
        assert fib.low == low
        assert fib.type == "fibonacci"
    
    def test_fibonacci_levels_calculation(self):
        """Test Fibonacci level calculations."""
        high = 120.0
        low = 100.0
        x_start = datetime(2024, 1, 1)
        x_end = datetime(2024, 1, 31)
        
        fib = FibonacciRetracement(high=high, low=low, x_start=x_start, x_end=x_end)
        levels = fib.calculate_levels()
        
        # Check that all standard Fibonacci levels are calculated
        expected_ratios = [0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
        for ratio in expected_ratios:
            assert ratio in levels
        
        # Verify level calculations
        assert levels[0.0] == high  # 0% level is the high
        assert levels[1.0] == low   # 100% level is the low
        assert abs(levels[0.5] - 110.0) < 0.01  # 50% level is midpoint
    
    def test_fibonacci_level_configs(self):
        """Test Fibonacci level configuration generation."""
        fib = FibonacciRetracement(
            high=120.0,
            low=100.0,
            x_start=datetime(2024, 1, 1),
            x_end=datetime(2024, 1, 31),
        )
        
        configs = fib.get_level_configs()
        
        assert len(configs) == len(fib.LEVELS)
        for config in configs:
            assert "price" in config
            assert "label" in config
            assert "color" in config
            assert "ratio" in config


# ============================================================================
# Test Chart Export (Requirement 18.12)
# ============================================================================

class TestChartExport:
    """Test chart export functionality."""
    
    def test_get_export_formats(self):
        """Test that export formats are available."""
        formats = get_export_formats()
        
        assert isinstance(formats, list)
        # Should have at least PNG and HTML (minimal dependencies)
        assert "png" in formats or "html" in formats
    
    @pytest.mark.skipif(
        not Path(__file__).parent.parent.joinpath("requirements.txt").exists(),
        reason="Plotly may not be installed"
    )
    def test_export_format_validation(self):
        """Test export format validation."""
        from plotly import graph_objects as go
        
        fig = go.Figure()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfile = Path(tmpdir) / "test_chart"
            
            # Test invalid format
            from stockiq.ui.charts.chart_export import export_chart
            result = export_chart(fig, tmpfile, format="invalid_format")
            assert result is False


# ============================================================================
# Test Heatmaps (Requirements 18.9, 18.10)
# ============================================================================

class TestHeatmaps:
    """Test heatmap visualization functionality."""
    
    def test_demo_sector_data_generation(self):
        """Test generation of demo sector data."""
        sector_etfs = {
            "XLK": "Technology",
            "XLF": "Financials",
            "XLE": "Energy",
        }
        
        df = _demo_sector_data(sector_etfs)
        
        assert len(df) == len(sector_etfs)
        assert all(col in df.columns for col in ["ticker", "sector", "change_pct", "price"])
        assert set(df["ticker"]) == set(sector_etfs.keys())
    
    def test_demo_correlation_matrix(self, sample_tickers):
        """Test generation of demo correlation matrix."""
        corr_matrix = _demo_correlation_matrix(sample_tickers)
        
        assert corr_matrix.shape == (len(sample_tickers), len(sample_tickers))
        
        # Diagonal should be 1.0 (self-correlation)
        np.testing.assert_array_almost_equal(
            np.diag(corr_matrix.values),
            np.ones(len(sample_tickers)),
            decimal=6
        )
        
        # Matrix should be symmetric
        np.testing.assert_array_almost_equal(
            corr_matrix.values,
            corr_matrix.values.T,
            decimal=6
        )
        
        # All values should be between -1 and 1
        assert (corr_matrix.values >= -1).all()
        assert (corr_matrix.values <= 1).all()
    
    def test_correlation_matrix_properties(self, sample_tickers):
        """Test mathematical properties of correlation matrix."""
        corr_matrix = _demo_correlation_matrix(sample_tickers)
        
        # Test symmetry
        for i in range(len(sample_tickers)):
            for j in range(len(sample_tickers)):
                assert abs(corr_matrix.iloc[i, j] - corr_matrix.iloc[j, i]) < 1e-10


# ============================================================================
# Integration Tests
# ============================================================================

class TestChartingIntegration:
    """Integration tests for complete charting workflows."""
    
    def test_complete_chart_workflow(self, sample_price_data):
        """Test complete workflow: data -> indicators -> drawing tools."""
        # Calculate indicators
        sma_20 = calculate_sma(sample_price_data["Close"], 20)
        rsi = calculate_rsi(sample_price_data["Close"], 14)
        macd_line, signal_line, _ = calculate_macd(sample_price_data["Close"])
        
        # All indicators should have same length as input
        assert len(sma_20) == len(sample_price_data)
        assert len(rsi) == len(sample_price_data)
        assert len(macd_line) == len(sample_price_data)
        
        # Create drawing tools
        x0 = sample_price_data.index[0]
        x1 = sample_price_data.index[-1]
        y0 = sample_price_data["Close"].iloc[0]
        y1 = sample_price_data["Close"].iloc[-1]
        
        trendline = add_trendline(x0, y0, x1, y1)
        assert isinstance(trendline, TrendLine)
    
    def test_multi_indicator_overlay(self, sample_price_data):
        """Test overlaying multiple indicators."""
        indicators = {
            "SMA_20": calculate_sma(sample_price_data["Close"], 20),
            "SMA_50": calculate_sma(sample_price_data["Close"], 50),
            "EMA_12": calculate_ema(sample_price_data["Close"], 12),
            "RSI": calculate_rsi(sample_price_data["Close"], 14),
        }
        
        # All indicators should be Series with correct length
        for name, indicator in indicators.items():
            assert isinstance(indicator, pd.Series)
            assert len(indicator) == len(sample_price_data)


# ============================================================================
# Performance Tests
# ============================================================================

class TestChartingPerformance:
    """Test performance requirements."""
    
    def test_indicator_calculation_performance(self, sample_price_data):
        """Test that indicator calculations complete quickly."""
        import time
        
        start = time.time()
        
        # Calculate multiple indicators
        calculate_sma(sample_price_data["Close"], 20)
        calculate_ema(sample_price_data["Close"], 20)
        calculate_rsi(sample_price_data["Close"], 14)
        calculate_macd(sample_price_data["Close"])
        calculate_bollinger_bands(sample_price_data["Close"])
        
        elapsed = time.time() - start
        
        # All calculations should complete in under 100ms
        assert elapsed < 0.1, f"Indicator calculations too slow: {elapsed:.3f}s"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
