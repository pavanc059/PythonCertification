"""
Tests for Options Greeks Calculator

Tests Requirements:
- 14.1: Calculate Delta, Gamma, Theta, Vega, Rho
- 14.2: Compute implied volatility surfaces
"""

import pytest
import numpy as np
from datetime import date, timedelta
from stockiq.analytics.options.greeks import (
    OptionsAnalyzer,
    OptionContract,
    Greeks,
    VolatilitySurface
)


@pytest.fixture
def analyzer():
    """Create OptionsAnalyzer instance"""
    return OptionsAnalyzer()


@pytest.fixture
def sample_call_option():
    """Create sample call option for testing"""
    expiration = date.today() + timedelta(days=30)
    return OptionContract(
        ticker='AAPL',
        strike=100.0,
        expiration=expiration,
        option_type='call',
        underlying_price=100.0,
        risk_free_rate=0.05,
        dividend_yield=0.0,
        market_price=5.0
    )


@pytest.fixture
def sample_put_option():
    """Create sample put option for testing"""
    expiration = date.today() + timedelta(days=30)
    return OptionContract(
        ticker='AAPL',
        strike=100.0,
        expiration=expiration,
        option_type='put',
        underlying_price=100.0,
        risk_free_rate=0.05,
        dividend_yield=0.0,
        market_price=5.0
    )


class TestGreeksCalculation:
    """Test Greeks calculation for options (Requirement 14.1)"""
    
    def test_call_delta_range(self, analyzer, sample_call_option):
        """Test that call option delta is between 0 and 1"""
        greeks = analyzer.calculate_greeks(sample_call_option, volatility=0.20)
        assert 0 <= greeks.delta <= 1, f"Call delta {greeks.delta} out of range [0, 1]"
    
    def test_put_delta_range(self, analyzer, sample_put_option):
        """Test that put option delta is between -1 and 0"""
        greeks = analyzer.calculate_greeks(sample_put_option, volatility=0.20)
        assert -1 <= greeks.delta <= 0, f"Put delta {greeks.delta} out of range [-1, 0]"
    
    def test_atm_call_delta_approximately_half(self, analyzer, sample_call_option):
        """Test that ATM call delta is approximately 0.5"""
        greeks = analyzer.calculate_greeks(sample_call_option, volatility=0.20)
        # ATM call delta with no dividends should be around 0.5
        assert 0.45 <= greeks.delta <= 0.55, f"ATM call delta {greeks.delta} not near 0.5"
    
    def test_itm_call_higher_delta(self, analyzer, sample_call_option):
        """Test that ITM call has higher delta than ATM call"""
        # ITM call (spot > strike)
        itm_call = sample_call_option
        itm_call.underlying_price = 110.0
        itm_greeks = analyzer.calculate_greeks(itm_call, volatility=0.20)
        
        # ATM call
        atm_call = sample_call_option
        atm_call.underlying_price = 100.0
        atm_greeks = analyzer.calculate_greeks(atm_call, volatility=0.20)
        
        assert itm_greeks.delta > atm_greeks.delta, "ITM call should have higher delta"
    
    def test_otm_call_lower_delta(self, analyzer, sample_call_option):
        """Test that OTM call has lower delta than ATM call"""
        # OTM call (spot < strike)
        otm_call = sample_call_option
        otm_call.underlying_price = 90.0
        otm_greeks = analyzer.calculate_greeks(otm_call, volatility=0.20)
        
        # ATM call
        atm_call = sample_call_option
        atm_call.underlying_price = 100.0
        atm_greeks = analyzer.calculate_greeks(atm_call, volatility=0.20)
        
        assert otm_greeks.delta < atm_greeks.delta, "OTM call should have lower delta"
    
    def test_gamma_always_positive(self, analyzer, sample_call_option):
        """Test that gamma is always positive for both calls and puts"""
        call_greeks = analyzer.calculate_greeks(sample_call_option, volatility=0.20)
        assert call_greeks.gamma > 0, f"Call gamma {call_greeks.gamma} should be positive"
        
        put_option = sample_call_option
        put_option.option_type = 'put'
        put_greeks = analyzer.calculate_greeks(put_option, volatility=0.20)
        assert put_greeks.gamma > 0, f"Put gamma {put_greeks.gamma} should be positive"
    
    def test_gamma_highest_at_atm(self, analyzer, sample_call_option):
        """Test that gamma is highest for ATM options"""
        # ATM
        atm_call = sample_call_option
        atm_call.underlying_price = 100.0
        atm_greeks = analyzer.calculate_greeks(atm_call, volatility=0.20)
        
        # ITM
        itm_call = sample_call_option
        itm_call.underlying_price = 110.0
        itm_greeks = analyzer.calculate_greeks(itm_call, volatility=0.20)
        
        # OTM
        otm_call = sample_call_option
        otm_call.underlying_price = 90.0
        otm_greeks = analyzer.calculate_greeks(otm_call, volatility=0.20)
        
        assert atm_greeks.gamma > itm_greeks.gamma, "ATM gamma should be higher than ITM"
        assert atm_greeks.gamma > otm_greeks.gamma, "ATM gamma should be higher than OTM"
    
    def test_theta_negative_for_long_options(self, analyzer, sample_call_option):
        """Test that theta is negative (time decay) for long options"""
        call_greeks = analyzer.calculate_greeks(sample_call_option, volatility=0.20)
        assert call_greeks.theta < 0, f"Call theta {call_greeks.theta} should be negative"
        
        put_option = sample_call_option
        put_option.option_type = 'put'
        put_greeks = analyzer.calculate_greeks(put_option, volatility=0.20)
        assert put_greeks.theta < 0, f"Put theta {put_greeks.theta} should be negative"
    
    def test_vega_always_positive(self, analyzer, sample_call_option):
        """Test that vega is always positive"""
        call_greeks = analyzer.calculate_greeks(sample_call_option, volatility=0.20)
        assert call_greeks.vega > 0, f"Call vega {call_greeks.vega} should be positive"
        
        put_option = sample_call_option
        put_option.option_type = 'put'
        put_greeks = analyzer.calculate_greeks(put_option, volatility=0.20)
        assert put_greeks.vega > 0, f"Put vega {put_greeks.vega} should be positive"
    
    def test_vega_same_for_calls_and_puts(self, analyzer, sample_call_option):
        """Test that vega is the same for calls and puts with same parameters"""
        call_greeks = analyzer.calculate_greeks(sample_call_option, volatility=0.20)
        
        put_option = sample_call_option
        put_option.option_type = 'put'
        put_greeks = analyzer.calculate_greeks(put_option, volatility=0.20)
        
        # Vega should be identical (within floating point precision)
        assert abs(call_greeks.vega - put_greeks.vega) < 0.001, \
            f"Call and put vega should be equal: {call_greeks.vega} vs {put_greeks.vega}"
    
    def test_call_rho_positive(self, analyzer, sample_call_option):
        """Test that call option rho is positive"""
        greeks = analyzer.calculate_greeks(sample_call_option, volatility=0.20)
        assert greeks.rho > 0, f"Call rho {greeks.rho} should be positive"
    
    def test_put_rho_negative(self, analyzer, sample_put_option):
        """Test that put option rho is negative"""
        greeks = analyzer.calculate_greeks(sample_put_option, volatility=0.20)
        assert greeks.rho < 0, f"Put rho {greeks.rho} should be negative"
    
    def test_expired_option_zero_greeks(self, analyzer):
        """Test that expired options have zero Greeks"""
        expired_option = OptionContract(
            ticker='AAPL',
            strike=100.0,
            expiration=date.today() - timedelta(days=1),  # Expired
            option_type='call',
            underlying_price=100.0,
            risk_free_rate=0.05,
        )
        
        greeks = analyzer.calculate_greeks(expired_option, volatility=0.20)
        assert greeks.delta == 0.0
        assert greeks.gamma == 0.0
        assert greeks.theta == 0.0
        assert greeks.vega == 0.0
        assert greeks.rho == 0.0
    
    def test_greeks_with_dividends(self, analyzer, sample_call_option):
        """Test Greeks calculation with dividend yield"""
        sample_call_option.dividend_yield = 0.02  # 2% dividend yield
        greeks = analyzer.calculate_greeks(sample_call_option, volatility=0.20)
        
        # With dividends, call delta should be slightly lower
        assert 0 <= greeks.delta <= 1
        assert greeks.gamma > 0
        assert greeks.theta < 0
        assert greeks.vega > 0
        assert greeks.rho > 0


class TestImpliedVolatility:
    """Test implied volatility calculation (Requirement 14.2)"""
    
    def test_implied_volatility_recovery(self, analyzer, sample_call_option):
        """Test that we can recover implied volatility from theoretical price"""
        # Calculate theoretical price with known volatility
        known_vol = 0.25
        theoretical_price = analyzer._black_scholes_price(sample_call_option, known_vol)
        
        # Set as market price and calculate IV
        sample_call_option.market_price = theoretical_price
        implied_vol = analyzer.calculate_implied_volatility(sample_call_option)
        
        # Should recover the original volatility
        assert implied_vol is not None
        assert abs(implied_vol - known_vol) < 0.001, \
            f"IV {implied_vol} should match known vol {known_vol}"
    
    def test_implied_volatility_range(self, analyzer, sample_call_option):
        """Test that implied volatility is in reasonable range"""
        sample_call_option.market_price = 5.0
        implied_vol = analyzer.calculate_implied_volatility(sample_call_option)
        
        if implied_vol is not None:
            assert 0.01 <= implied_vol <= 3.0, \
                f"IV {implied_vol} out of reasonable range [0.01, 3.0]"
    
    def test_implied_volatility_put_option(self, analyzer, sample_put_option):
        """Test IV calculation for put option"""
        # Calculate theoretical price
        known_vol = 0.30
        theoretical_price = analyzer._black_scholes_price(sample_put_option, known_vol)
        
        sample_put_option.market_price = theoretical_price
        implied_vol = analyzer.calculate_implied_volatility(sample_put_option)
        
        assert implied_vol is not None
        assert abs(implied_vol - known_vol) < 0.001
    
    def test_implied_volatility_no_market_price(self, analyzer, sample_call_option):
        """Test that IV returns None when no market price provided"""
        sample_call_option.market_price = None
        implied_vol = analyzer.calculate_implied_volatility(sample_call_option)
        assert implied_vol is None
    
    def test_implied_volatility_expired_option(self, analyzer):
        """Test that IV returns None for expired options"""
        expired_option = OptionContract(
            ticker='AAPL',
            strike=100.0,
            expiration=date.today() - timedelta(days=1),
            option_type='call',
            underlying_price=100.0,
            risk_free_rate=0.05,
            market_price=5.0
        )
        
        implied_vol = analyzer.calculate_implied_volatility(expired_option)
        assert implied_vol is None
    
    def test_implied_volatility_below_intrinsic(self, analyzer, sample_call_option):
        """Test that IV returns None when price below intrinsic value"""
        sample_call_option.underlying_price = 110.0  # ITM
        sample_call_option.strike = 100.0
        sample_call_option.market_price = 5.0  # Below intrinsic value of 10
        
        implied_vol = analyzer.calculate_implied_volatility(sample_call_option)
        assert implied_vol is None


class TestVolatilitySurface:
    """Test volatility surface generation (Requirement 14.2)"""
    
    def test_volatility_surface_creation(self, analyzer):
        """Test basic volatility surface generation"""
        expiration1 = date.today() + timedelta(days=30)
        expiration2 = date.today() + timedelta(days=60)
        
        options_chain = []
        strikes = [95.0, 100.0, 105.0]
        expirations = [expiration1, expiration2]
        
        # Create options grid
        for exp in expirations:
            for strike in strikes:
                # Calculate theoretical price for known volatility
                vol = 0.25
                option = OptionContract(
                    ticker='AAPL',
                    strike=strike,
                    expiration=exp,
                    option_type='call',
                    underlying_price=100.0,
                    risk_free_rate=0.05
                )
                option.market_price = analyzer._black_scholes_price(option, vol)
                options_chain.append(option)
        
        surface = analyzer.generate_volatility_surface('AAPL', options_chain)
        
        assert surface.ticker == 'AAPL'
        assert surface.strikes == strikes
        assert surface.expirations == expirations
        assert surface.implied_vols.shape == (len(expirations), len(strikes))
    
    def test_volatility_surface_values(self, analyzer):
        """Test that volatility surface contains reasonable values"""
        expiration = date.today() + timedelta(days=30)
        strikes = [90.0, 95.0, 100.0, 105.0, 110.0]
        
        options_chain = []
        for strike in strikes:
            vol = 0.20 + 0.05 * abs(100 - strike) / 10  # Volatility smile
            option = OptionContract(
                ticker='AAPL',
                strike=strike,
                expiration=expiration,
                option_type='call',
                underlying_price=100.0,
                risk_free_rate=0.05
            )
            option.market_price = analyzer._black_scholes_price(option, vol)
            options_chain.append(option)
        
        surface = analyzer.generate_volatility_surface('AAPL', options_chain)
        
        # Check all values are within reasonable range
        assert np.all(surface.implied_vols >= 0.01)
        assert np.all(surface.implied_vols <= 1.0)
    
    def test_volatility_surface_empty_chain(self, analyzer):
        """Test that empty options chain raises ValueError"""
        with pytest.raises(ValueError, match="Options chain is empty"):
            analyzer.generate_volatility_surface('AAPL', [])
    
    def test_volatility_surface_interpolation(self, analyzer):
        """Test that surface interpolates missing values"""
        expiration = date.today() + timedelta(days=30)
        strikes = [90.0, 95.0, 100.0, 105.0, 110.0]
        
        options_chain = []
        # Only provide options for strikes 90, 100, 110 (skip 95 and 105)
        for strike in [90.0, 100.0, 110.0]:
            vol = 0.25
            option = OptionContract(
                ticker='AAPL',
                strike=strike,
                expiration=expiration,
                option_type='call',
                underlying_price=100.0,
                risk_free_rate=0.05
            )
            option.market_price = analyzer._black_scholes_price(option, vol)
            options_chain.append(option)
        
        surface = analyzer.generate_volatility_surface('AAPL', options_chain)
        
        # Check that interpolation filled missing strikes
        assert not np.any(np.isnan(surface.implied_vols))


class TestBlackScholesPrice:
    """Test Black-Scholes pricing formula"""
    
    def test_call_price_positive(self, analyzer, sample_call_option):
        """Test that call option price is always positive"""
        price = analyzer._black_scholes_price(sample_call_option, volatility=0.20)
        assert price > 0
    
    def test_put_price_positive(self, analyzer, sample_put_option):
        """Test that put option price is always positive"""
        price = analyzer._black_scholes_price(sample_put_option, volatility=0.20)
        assert price > 0
    
    def test_deep_itm_call_near_intrinsic(self, analyzer, sample_call_option):
        """Test that deep ITM call price approaches intrinsic value"""
        sample_call_option.underlying_price = 150.0
        sample_call_option.strike = 100.0
        
        price = analyzer._black_scholes_price(sample_call_option, volatility=0.20)
        intrinsic = 150.0 - 100.0
        
        # Price should be close to intrinsic for deep ITM
        assert price >= intrinsic
        assert price < intrinsic + 10  # Time value should be small
    
    def test_deep_otm_call_near_zero(self, analyzer, sample_call_option):
        """Test that deep OTM call price approaches zero"""
        sample_call_option.underlying_price = 50.0
        sample_call_option.strike = 100.0
        
        price = analyzer._black_scholes_price(sample_call_option, volatility=0.20)
        assert price < 1.0  # Very small price for deep OTM
    
    def test_expired_option_intrinsic_value(self, analyzer):
        """Test that expired option returns intrinsic value"""
        expired_call = OptionContract(
            ticker='AAPL',
            strike=100.0,
            expiration=date.today() - timedelta(days=1),
            option_type='call',
            underlying_price=110.0,
            risk_free_rate=0.05
        )
        
        price = analyzer._black_scholes_price(expired_call, volatility=0.20)
        assert price == 10.0  # Intrinsic value only
    
    def test_put_call_parity(self, analyzer, sample_call_option):
        """Test put-call parity: C - P = S - K*exp(-rT)"""
        volatility = 0.25
        
        # Call price
        call_price = analyzer._black_scholes_price(sample_call_option, volatility)
        
        # Put price (same parameters)
        put_option = sample_call_option
        put_option.option_type = 'put'
        put_price = analyzer._black_scholes_price(put_option, volatility)
        
        # Put-call parity
        S = sample_call_option.underlying_price
        K = sample_call_option.strike
        r = sample_call_option.risk_free_rate
        T = analyzer._time_to_expiration(sample_call_option.expiration)
        
        lhs = call_price - put_price
        rhs = S - K * np.exp(-r * T)
        
        # Should satisfy parity (within numerical precision)
        assert abs(lhs - rhs) < 0.01, \
            f"Put-call parity violated: {lhs} != {rhs}"


class TestTimeToExpiration:
    """Test time to expiration calculation"""
    
    def test_time_to_expiration_future(self, analyzer):
        """Test time calculation for future expiration"""
        future_date = date.today() + timedelta(days=365)
        T = analyzer._time_to_expiration(future_date)
        assert 0.99 <= T <= 1.01  # Approximately 1 year
    
    def test_time_to_expiration_past(self, analyzer):
        """Test that past expiration returns 0"""
        past_date = date.today() - timedelta(days=10)
        T = analyzer._time_to_expiration(past_date)
        assert T == 0.0
    
    def test_time_to_expiration_today(self, analyzer):
        """Test that expiration today returns 0"""
        T = analyzer._time_to_expiration(date.today())
        assert T == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
