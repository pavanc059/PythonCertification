"""
Options Greeks Calculator

Calculates options Greeks (Delta, Gamma, Theta, Vega, Rho) using the Black-Scholes model
and generates implied volatility surfaces across strike prices and expiration dates.

Requirements:
- 14.1: Calculate options Greeks (Delta, Gamma, Theta, Vega, Rho)
- 14.2: Compute implied volatility surfaces across strikes and expirations
"""

from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional, Dict
import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
import logging

logger = logging.getLogger(__name__)


@dataclass
class OptionContract:
    """Represents an options contract"""
    ticker: str
    strike: float
    expiration: date
    option_type: str  # 'call' or 'put'
    underlying_price: float
    risk_free_rate: float = 0.05  # Default 5%
    dividend_yield: float = 0.0   # Default 0%
    market_price: Optional[float] = None  # Current market price of option


@dataclass
class Greeks:
    """Options Greeks sensitivity measures
    
    Attributes:
        delta: Rate of change of option price w.r.t. underlying price (-1 to 1)
        gamma: Rate of change of delta w.r.t. underlying price (>= 0)
        theta: Rate of change of option price w.r.t. time (usually negative)
        vega: Rate of change of option price w.r.t. volatility (>= 0)
        rho: Rate of change of option price w.r.t. risk-free rate
    """
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float


@dataclass
class VolatilitySurface:
    """Implied volatility surface across strikes and expirations
    
    Attributes:
        ticker: Stock ticker symbol
        strikes: List of strike prices
        expirations: List of expiration dates
        implied_vols: 2D numpy array of implied volatilities
                     Shape: (len(expirations), len(strikes))
    """
    ticker: str
    strikes: List[float]
    expirations: List[date]
    implied_vols: np.ndarray  # 2D array: rows=expirations, cols=strikes


class OptionsAnalyzer:
    """Calculates options Greeks and implied volatility metrics
    
    Uses the Black-Scholes-Merton model for European-style options.
    All calculations account for continuous dividend yield.
    """
    
    def __init__(self):
        """Initialize the options analyzer"""
        self.logger = logging.getLogger(__name__)
    
    def calculate_greeks(self, option: OptionContract, 
                        volatility: float) -> Greeks:
        """Calculate all Greeks for an option contract
        
        Args:
            option: OptionContract with underlying price, strike, expiration, etc.
            volatility: Annualized volatility (e.g., 0.20 for 20%)
        
        Returns:
            Greeks object with all sensitivity measures
            
        Requirements:
            - 14.1: Calculate Delta, Gamma, Theta, Vega, Rho
        """
        T = self._time_to_expiration(option.expiration)
        
        if T <= 0:
            # Option expired - intrinsic value only, no Greeks
            return Greeks(delta=0.0, gamma=0.0, theta=0.0, vega=0.0, rho=0.0)
        
        S = option.underlying_price
        K = option.strike
        r = option.risk_free_rate
        q = option.dividend_yield
        sigma = volatility
        
        # Calculate d1 and d2 from Black-Scholes formula
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        # Standard normal PDF and CDF
        N_d1 = norm.cdf(d1)
        N_d2 = norm.cdf(d2)
        n_d1 = norm.pdf(d1)  # PDF for gamma and vega
        
        is_call = option.option_type.lower() == 'call'
        
        # Delta: ∂V/∂S
        if is_call:
            delta = np.exp(-q * T) * N_d1
        else:
            delta = -np.exp(-q * T) * (1 - N_d1)
        
        # Gamma: ∂²V/∂S² (same for calls and puts)
        gamma = np.exp(-q * T) * n_d1 / (S * sigma * np.sqrt(T))
        
        # Theta: ∂V/∂t (converted to per-day basis)
        if is_call:
            theta = (
                -S * n_d1 * sigma * np.exp(-q * T) / (2 * np.sqrt(T))
                - r * K * np.exp(-r * T) * N_d2
                + q * S * np.exp(-q * T) * N_d1
            ) / 365  # Convert to daily theta
        else:
            theta = (
                -S * n_d1 * sigma * np.exp(-q * T) / (2 * np.sqrt(T))
                + r * K * np.exp(-r * T) * (1 - N_d2)
                - q * S * np.exp(-q * T) * (1 - N_d1)
            ) / 365  # Convert to daily theta
        
        # Vega: ∂V/∂σ (same for calls and puts, divide by 100 for 1% change)
        vega = S * np.exp(-q * T) * n_d1 * np.sqrt(T) / 100
        
        # Rho: ∂V/∂r (divide by 100 for 1% change in interest rate)
        if is_call:
            rho = K * T * np.exp(-r * T) * N_d2 / 100
        else:
            rho = -K * T * np.exp(-r * T) * (1 - N_d2) / 100
        
        return Greeks(
            delta=float(delta),
            gamma=float(gamma),
            theta=float(theta),
            vega=float(vega),
            rho=float(rho)
        )
    
    def calculate_implied_volatility(self, option: OptionContract) -> Optional[float]:
        """Calculate implied volatility from option market price using Newton-Raphson
        
        Args:
            option: OptionContract with market_price set
        
        Returns:
            Implied volatility (annualized), or None if calculation fails
            
        Requirements:
            - 14.2: Compute implied volatility from market prices
        """
        if option.market_price is None:
            self.logger.warning("Market price not provided for option")
            return None
        
        T = self._time_to_expiration(option.expiration)
        if T <= 0:
            self.logger.warning("Option expired, cannot calculate IV")
            return None
        
        market_price = option.market_price
        
        # Intrinsic value bounds
        S = option.underlying_price
        K = option.strike
        is_call = option.option_type.lower() == 'call'
        
        intrinsic = max(0, (S - K) if is_call else (K - S))
        
        if market_price < intrinsic:
            self.logger.warning(f"Market price ${market_price:.2f} below intrinsic ${intrinsic:.2f}")
            return None
        
        # Define objective function: market_price - theoretical_price = 0
        def objective(sigma: float) -> float:
            theoretical = self._black_scholes_price(option, sigma)
            return theoretical - market_price
        
        try:
            # Use Brent's method to find root (implied volatility)
            # Search between 0.01% and 500% volatility
            implied_vol = brentq(objective, 0.0001, 5.0, maxiter=100)
            return float(implied_vol)
        
        except (ValueError, RuntimeError) as e:
            self.logger.error(f"Failed to calculate implied volatility: {e}")
            return None
    
    def generate_volatility_surface(self, 
                                   ticker: str,
                                   options_chain: List[OptionContract]) -> VolatilitySurface:
        """Generate implied volatility surface across strikes and expirations
        
        Args:
            ticker: Stock ticker symbol
            options_chain: List of OptionContract objects with market prices
        
        Returns:
            VolatilitySurface with 2D grid of implied volatilities
            
        Requirements:
            - 14.2: Generate IV surface across strikes and expirations
        """
        if not options_chain:
            raise ValueError("Options chain is empty")
        
        # Extract unique strikes and expirations
        strikes = sorted(set(opt.strike for opt in options_chain))
        expirations = sorted(set(opt.expiration for opt in options_chain))
        
        # Initialize 2D array for implied vols (rows=expirations, cols=strikes)
        implied_vols = np.full((len(expirations), len(strikes)), np.nan)
        
        # Calculate implied volatility for each option
        for opt in options_chain:
            if opt.market_price is None:
                continue
            
            try:
                iv = self.calculate_implied_volatility(opt)
                if iv is not None:
                    exp_idx = expirations.index(opt.expiration)
                    strike_idx = strikes.index(opt.strike)
                    implied_vols[exp_idx, strike_idx] = iv
            
            except Exception as e:
                self.logger.warning(
                    f"Failed to calculate IV for {ticker} "
                    f"{opt.strike} {opt.expiration}: {e}"
                )
        
        # Interpolate missing values (simple linear interpolation)
        implied_vols = self._interpolate_surface(implied_vols)
        
        return VolatilitySurface(
            ticker=ticker,
            strikes=strikes,
            expirations=expirations,
            implied_vols=implied_vols
        )
    
    def _black_scholes_price(self, option: OptionContract, volatility: float) -> float:
        """Calculate theoretical option price using Black-Scholes-Merton formula
        
        Args:
            option: OptionContract
            volatility: Annualized volatility
        
        Returns:
            Theoretical option price
        """
        T = self._time_to_expiration(option.expiration)
        
        if T <= 0:
            # Expired option - return intrinsic value
            S = option.underlying_price
            K = option.strike
            is_call = option.option_type.lower() == 'call'
            return max(0, (S - K) if is_call else (K - S))
        
        S = option.underlying_price
        K = option.strike
        r = option.risk_free_rate
        q = option.dividend_yield
        sigma = volatility
        
        # Calculate d1 and d2
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        
        is_call = option.option_type.lower() == 'call'
        
        if is_call:
            price = (
                S * np.exp(-q * T) * norm.cdf(d1)
                - K * np.exp(-r * T) * norm.cdf(d2)
            )
        else:
            price = (
                K * np.exp(-r * T) * norm.cdf(-d2)
                - S * np.exp(-q * T) * norm.cdf(-d1)
            )
        
        return float(price)
    
    def _time_to_expiration(self, expiration: date) -> float:
        """Calculate time to expiration in years
        
        Args:
            expiration: Expiration date
        
        Returns:
            Time to expiration in years (365-day calendar)
        """
        now = datetime.now().date()
        days_to_expiration = (expiration - now).days
        return max(0, days_to_expiration / 365.0)
    
    def _interpolate_surface(self, surface: np.ndarray) -> np.ndarray:
        """Interpolate missing values in volatility surface
        
        Uses linear interpolation along each axis to fill NaN values.
        
        Args:
            surface: 2D array with possible NaN values
        
        Returns:
            2D array with interpolated values
        """
        surface_copy = surface.copy()
        
        # Interpolate along strike axis (columns) for each expiration
        for i in range(surface_copy.shape[0]):
            row = surface_copy[i, :]
            valid_mask = ~np.isnan(row)
            
            if valid_mask.sum() >= 2:  # Need at least 2 points to interpolate
                valid_indices = np.where(valid_mask)[0]
                valid_values = row[valid_mask]
                
                # Linear interpolation
                surface_copy[i, :] = np.interp(
                    np.arange(len(row)),
                    valid_indices,
                    valid_values,
                    left=valid_values[0],
                    right=valid_values[-1]
                )
        
        # Interpolate along expiration axis (rows) for each strike
        for j in range(surface_copy.shape[1]):
            col = surface_copy[:, j]
            valid_mask = ~np.isnan(col)
            
            if valid_mask.sum() >= 2:
                valid_indices = np.where(valid_mask)[0]
                valid_values = col[valid_mask]
                
                surface_copy[:, j] = np.interp(
                    np.arange(len(col)),
                    valid_indices,
                    valid_values,
                    left=valid_values[0],
                    right=valid_values[-1]
                )
        
        return surface_copy
