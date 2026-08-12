"""
Options Greeks Calculator Demo

Demonstrates the OptionsAnalyzer capabilities including:
- Greeks calculation (Delta, Gamma, Theta, Vega, Rho)
- Implied volatility calculation
- Volatility surface generation
"""

from datetime import date, timedelta
import numpy as np
from stockiq.analytics.options.greeks import (
    OptionsAnalyzer,
    OptionContract,
    Greeks,
    VolatilitySurface
)


def demo_greeks_calculation():
    """Demonstrate Greeks calculation for different option scenarios"""
    print("=" * 80)
    print("GREEKS CALCULATION DEMO")
    print("=" * 80)
    
    analyzer = OptionsAnalyzer()
    expiration = date.today() + timedelta(days=30)
    volatility = 0.25  # 25% volatility
    
    # Scenario 1: ATM Call Option
    print("\n1. AT-THE-MONEY CALL OPTION")
    print("-" * 40)
    atm_call = OptionContract(
        ticker='AAPL',
        strike=150.0,
        expiration=expiration,
        option_type='call',
        underlying_price=150.0,
        risk_free_rate=0.05,
        dividend_yield=0.01
    )
    
    greeks = analyzer.calculate_greeks(atm_call, volatility)
    print(f"Strike: ${atm_call.strike:.2f}")
    print(f"Spot: ${atm_call.underlying_price:.2f}")
    print(f"Delta: {greeks.delta:.4f} (change per $1 move in stock)")
    print(f"Gamma: {greeks.gamma:.4f} (change in delta per $1 move)")
    print(f"Theta: ${greeks.theta:.4f} per day (time decay)")
    print(f"Vega: ${greeks.vega:.4f} per 1% vol change")
    print(f"Rho: ${greeks.rho:.4f} per 1% rate change")
    
    # Scenario 2: ITM Call Option
    print("\n2. IN-THE-MONEY CALL OPTION")
    print("-" * 40)
    itm_call = OptionContract(
        ticker='AAPL',
        strike=140.0,
        expiration=expiration,
        option_type='call',
        underlying_price=150.0,
        risk_free_rate=0.05,
        dividend_yield=0.01
    )
    
    greeks = analyzer.calculate_greeks(itm_call, volatility)
    print(f"Strike: ${itm_call.strike:.2f}")
    print(f"Spot: ${itm_call.underlying_price:.2f}")
    print(f"Intrinsic Value: ${itm_call.underlying_price - itm_call.strike:.2f}")
    print(f"Delta: {greeks.delta:.4f} (higher than ATM)")
    print(f"Gamma: {greeks.gamma:.4f} (lower than ATM)")
    
    # Scenario 3: OTM Put Option
    print("\n3. OUT-OF-THE-MONEY PUT OPTION")
    print("-" * 40)
    otm_put = OptionContract(
        ticker='AAPL',
        strike=140.0,
        expiration=expiration,
        option_type='put',
        underlying_price=150.0,
        risk_free_rate=0.05,
        dividend_yield=0.01
    )
    
    greeks = analyzer.calculate_greeks(otm_put, volatility)
    print(f"Strike: ${otm_put.strike:.2f}")
    print(f"Spot: ${otm_put.underlying_price:.2f}")
    print(f"Delta: {greeks.delta:.4f} (negative for puts)")
    print(f"Gamma: {greeks.gamma:.4f} (same as call with same params)")
    print(f"Rho: ${greeks.rho:.4f} (negative for puts)")


def demo_implied_volatility():
    """Demonstrate implied volatility calculation"""
    print("\n" + "=" * 80)
    print("IMPLIED VOLATILITY DEMO")
    print("=" * 80)
    
    analyzer = OptionsAnalyzer()
    expiration = date.today() + timedelta(days=45)
    
    # Create an option with a known market price
    option = OptionContract(
        ticker='TSLA',
        strike=200.0,
        expiration=expiration,
        option_type='call',
        underlying_price=210.0,
        risk_free_rate=0.05,
        dividend_yield=0.0,
        market_price=15.50  # Observed market price
    )
    
    print(f"\nOption Details:")
    print(f"  Ticker: {option.ticker}")
    print(f"  Type: {option.option_type.upper()}")
    print(f"  Strike: ${option.strike:.2f}")
    print(f"  Spot Price: ${option.underlying_price:.2f}")
    print(f"  Market Price: ${option.market_price:.2f}")
    print(f"  Days to Expiration: {(expiration - date.today()).days}")
    
    # Calculate implied volatility
    implied_vol = analyzer.calculate_implied_volatility(option)
    
    if implied_vol is not None:
        print(f"\nImplied Volatility: {implied_vol:.2%}")
        
        # Verify by calculating theoretical price with the IV
        theoretical_price = analyzer._black_scholes_price(option, implied_vol)
        print(f"Verification - Theoretical Price: ${theoretical_price:.2f}")
        print(f"Difference: ${abs(theoretical_price - option.market_price):.4f}")
    else:
        print("\nFailed to calculate implied volatility")


def demo_volatility_surface():
    """Demonstrate volatility surface generation"""
    print("\n" + "=" * 80)
    print("VOLATILITY SURFACE DEMO")
    print("=" * 80)
    
    analyzer = OptionsAnalyzer()
    
    # Create a synthetic options chain
    strikes = [140, 145, 150, 155, 160]  # Strike prices
    expirations = [
        date.today() + timedelta(days=30),
        date.today() + timedelta(days=60),
        date.today() + timedelta(days=90)
    ]
    
    print(f"\nGenerating volatility surface for NVDA")
    print(f"Strikes: {strikes}")
    print(f"Expirations: {[exp.strftime('%Y-%m-%d') for exp in expirations]}")
    
    options_chain = []
    
    # Generate synthetic options with volatility smile
    for exp_idx, exp in enumerate(expirations):
        for strike in strikes:
            # Simulate volatility smile (higher IV for OTM options)
            base_vol = 0.30 + 0.10 * exp_idx / len(expirations)  # Term structure
            strike_adjustment = 0.05 * abs(150 - strike) / 10  # Smile
            true_vol = base_vol + strike_adjustment
            
            # Create option
            option = OptionContract(
                ticker='NVDA',
                strike=float(strike),
                expiration=exp,
                option_type='call',
                underlying_price=150.0,
                risk_free_rate=0.05,
                dividend_yield=0.0
            )
            
            # Calculate theoretical price with known volatility
            option.market_price = analyzer._black_scholes_price(option, true_vol)
            options_chain.append(option)
    
    # Generate volatility surface
    surface = analyzer.generate_volatility_surface('NVDA', options_chain)
    
    print(f"\nVolatility Surface Generated:")
    print(f"  Ticker: {surface.ticker}")
    print(f"  Strikes: {surface.strikes}")
    print(f"  Shape: {surface.implied_vols.shape} (expirations × strikes)")
    
    print(f"\nImplied Volatilities (%):")
    print(f"{'Strike':<10}", end="")
    for exp in expirations:
        print(f"{exp.strftime('%m/%d'):<10}", end="")
    print()
    print("-" * 50)
    
    for strike_idx, strike in enumerate(surface.strikes):
        print(f"${strike:<9.0f}", end="")
        for exp_idx in range(len(surface.expirations)):
            iv = surface.implied_vols[exp_idx, strike_idx]
            print(f"{iv*100:>8.2f}%  ", end="")
        print()
    
    # Analyze the surface
    print(f"\nSurface Statistics:")
    print(f"  Mean IV: {np.nanmean(surface.implied_vols):.2%}")
    print(f"  Min IV: {np.nanmin(surface.implied_vols):.2%}")
    print(f"  Max IV: {np.nanmax(surface.implied_vols):.2%}")
    print(f"  Std Dev: {np.nanstd(surface.implied_vols):.2%}")


def demo_greeks_behavior():
    """Demonstrate how Greeks change with market conditions"""
    print("\n" + "=" * 80)
    print("GREEKS BEHAVIOR DEMO")
    print("=" * 80)
    
    analyzer = OptionsAnalyzer()
    expiration = date.today() + timedelta(days=30)
    volatility = 0.25
    
    print("\nHow Greeks Change with Stock Price (Call Option, K=$150)")
    print("-" * 70)
    print(f"{'Spot':<10} {'Delta':<10} {'Gamma':<10} {'Theta':<10} {'Vega':<10}")
    print("-" * 70)
    
    for spot in [130, 140, 150, 160, 170]:
        option = OptionContract(
            ticker='AAPL',
            strike=150.0,
            expiration=expiration,
            option_type='call',
            underlying_price=float(spot),
            risk_free_rate=0.05,
            dividend_yield=0.01
        )
        
        greeks = analyzer.calculate_greeks(option, volatility)
        print(f"${spot:<9.0f} {greeks.delta:<10.4f} {greeks.gamma:<10.4f} "
              f"${greeks.theta:<9.2f} ${greeks.vega:<9.2f}")
    
    print("\nKey Observations:")
    print("  • Delta increases as option goes deeper ITM (approaching 1.0)")
    print("  • Gamma is highest at ATM (strike = spot)")
    print("  • Theta is most negative near ATM (maximum time decay)")
    print("  • Vega is highest at ATM (most sensitive to volatility)")


def main():
    """Run all demonstrations"""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "OPTIONS GREEKS CALCULATOR DEMO" + " " * 28 + "║")
    print("╚" + "=" * 78 + "╝")
    
    try:
        demo_greeks_calculation()
        demo_implied_volatility()
        demo_volatility_surface()
        demo_greeks_behavior()
        
        print("\n" + "=" * 80)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\nThe OptionsAnalyzer provides institutional-grade options analytics:")
        print("  ✓ Comprehensive Greeks calculation (Delta, Gamma, Theta, Vega, Rho)")
        print("  ✓ Robust implied volatility calculation")
        print("  ✓ 2D volatility surface generation")
        print("  ✓ Support for calls, puts, and dividend-paying stocks")
        print("  ✓ Handles edge cases gracefully (expired options, missing data)")
        print("\n")
    
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
