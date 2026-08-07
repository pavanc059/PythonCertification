"""
Portfolio tracking and performance analysis.

Implements Requirements 16.9-16.10:
- Daily P&L tracking (16.9)
- Benchmark comparison (16.10)
"""

from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
import yfinance as yf
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Position:
    """
    Represents a position in the portfolio
    
    Attributes:
        ticker: Stock ticker symbol
        quantity: Number of shares
        avg_entry_price: Average entry price
        current_price: Current market price
        entry_time: Time of first entry
        last_updated: Last price update time
    """
    ticker: str
    quantity: int
    avg_entry_price: Decimal
    current_price: Decimal
    entry_time: datetime
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def market_value(self) -> Decimal:
        """Current market value of position"""
        return self.current_price * Decimal(self.quantity)
    
    @property
    def cost_basis(self) -> Decimal:
        """Total cost basis of position"""
        return self.avg_entry_price * Decimal(self.quantity)
    
    @property
    def unrealized_pnl(self) -> Decimal:
        """Unrealized profit/loss"""
        return self.market_value - self.cost_basis
    
    @property
    def unrealized_pnl_pct(self) -> float:
        """Unrealized profit/loss percentage"""
        if self.cost_basis == 0:
            return 0.0
        return float(self.unrealized_pnl / self.cost_basis)


class Portfolio:
    """
    Portfolio tracker with position management
    
    Features:
    - Position tracking
    - Real-time valuation
    - P&L calculation
    - Historical performance tracking
    """
    
    def __init__(self):
        """Initialize portfolio"""
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Dict] = []
        self.daily_snapshots: List[Dict] = []
    
    def add_position(
        self,
        ticker: str,
        quantity: int,
        price: Decimal,
        timestamp: datetime
    ) -> None:
        """
        Add to or create a position
        
        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares to add
            price: Purchase price
            timestamp: Transaction timestamp
        """
        if ticker in self.positions:
            # Add to existing position (calculate new average)
            position = self.positions[ticker]
            total_cost = position.cost_basis + (price * Decimal(quantity))
            total_quantity = position.quantity + quantity
            position.avg_entry_price = total_cost / Decimal(total_quantity)
            position.quantity = total_quantity
            position.last_updated = timestamp
        else:
            # Create new position
            self.positions[ticker] = Position(
                ticker=ticker,
                quantity=quantity,
                avg_entry_price=price,
                current_price=price,
                entry_time=timestamp,
                last_updated=timestamp
            )
        
        logger.info(
            "position_added",
            ticker=ticker,
            quantity=quantity,
            price=float(price)
        )
    
    def reduce_position(
        self,
        ticker: str,
        quantity: int,
        price: Decimal,
        timestamp: datetime
    ) -> Optional[Decimal]:
        """
        Reduce or close a position
        
        Args:
            ticker: Stock ticker symbol
            quantity: Number of shares to sell
            price: Sale price
            timestamp: Transaction timestamp
            
        Returns:
            Realized P&L or None if position doesn't exist
        """
        if ticker not in self.positions:
            logger.warning("position_not_found", ticker=ticker)
            return None
        
        position = self.positions[ticker]
        
        if quantity > position.quantity:
            logger.warning(
                "insufficient_shares",
                ticker=ticker,
                required=quantity,
                available=position.quantity
            )
            return None
        
        # Calculate realized P&L
        realized_pnl = (price - position.avg_entry_price) * Decimal(quantity)
        
        if quantity >= position.quantity:
            # Close entire position
            self.closed_positions.append({
                'ticker': ticker,
                'quantity': position.quantity,
                'avg_entry_price': position.avg_entry_price,
                'exit_price': price,
                'entry_time': position.entry_time,
                'exit_time': timestamp,
                'realized_pnl': realized_pnl,
                'realized_pnl_pct': float(realized_pnl / position.cost_basis)
            })
            
            del self.positions[ticker]
            
            logger.info(
                "position_closed",
                ticker=ticker,
                realized_pnl=float(realized_pnl)
            )
        else:
            # Partial reduction
            position.quantity -= quantity
            position.last_updated = timestamp
            
            self.closed_positions.append({
                'ticker': ticker,
                'quantity': quantity,
                'avg_entry_price': position.avg_entry_price,
                'exit_price': price,
                'entry_time': position.entry_time,
                'exit_time': timestamp,
                'realized_pnl': realized_pnl,
                'realized_pnl_pct': float(realized_pnl / (position.avg_entry_price * Decimal(quantity)))
            })
            
            logger.info(
                "position_reduced",
                ticker=ticker,
                quantity=quantity,
                remaining=position.quantity,
                realized_pnl=float(realized_pnl)
            )
        
        return realized_pnl
    
    def get_position(self, ticker: str) -> Optional[Position]:
        """
        Get position for a ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Position or None if not found
        """
        return self.positions.get(ticker)
    
    def update_prices(self, prices: Optional[Dict[str, Decimal]] = None) -> None:
        """
        Update current prices for all positions
        
        Args:
            prices: Optional dictionary of ticker -> price.
                   If None, fetches real-time prices from yfinance.
        """
        if prices is None:
            prices = {}
            for ticker in self.positions.keys():
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                    if current_price:
                        prices[ticker] = Decimal(str(current_price))
                except Exception as e:
                    logger.error("price_update_failed", ticker=ticker, error=str(e))
        
        for ticker, price in prices.items():
            if ticker in self.positions:
                self.positions[ticker].current_price = price
                self.positions[ticker].last_updated = datetime.utcnow()
    
    def get_total_value(self) -> Decimal:
        """
        Get total market value of all positions
        
        Returns:
            Total market value
        """
        return sum(position.market_value for position in self.positions.values())
    
    def get_total_cost_basis(self) -> Decimal:
        """
        Get total cost basis of all positions
        
        Returns:
            Total cost basis
        """
        return sum(position.cost_basis for position in self.positions.values())
    
    def get_unrealized_pnl(self) -> Decimal:
        """
        Get total unrealized P&L
        
        Returns:
            Total unrealized P&L
        """
        return sum(position.unrealized_pnl for position in self.positions.values())
    
    def get_realized_pnl(self) -> Decimal:
        """
        Get total realized P&L from closed positions
        
        Returns:
            Total realized P&L
        """
        return sum(Decimal(str(pos['realized_pnl'])) for pos in self.closed_positions)
    
    def take_daily_snapshot(self, skip_price_update: bool = False) -> Dict:
        """
        Take a snapshot of portfolio for daily tracking
        
        Args:
            skip_price_update: If True, don't update prices before snapshot
        
        Returns:
            Snapshot dictionary
        """
        if not skip_price_update:
            self.update_prices()
        
        snapshot = {
            'date': date.today(),
            'timestamp': datetime.utcnow(),
            'total_value': self.get_total_value(),
            'cost_basis': self.get_total_cost_basis(),
            'unrealized_pnl': self.get_unrealized_pnl(),
            'realized_pnl': self.get_realized_pnl(),
            'num_positions': len(self.positions),
            'positions': [
                {
                    'ticker': pos.ticker,
                    'quantity': pos.quantity,
                    'market_value': pos.market_value,
                    'unrealized_pnl': pos.unrealized_pnl,
                    'unrealized_pnl_pct': pos.unrealized_pnl_pct
                }
                for pos in self.positions.values()
            ]
        }
        
        self.daily_snapshots.append(snapshot)
        
        return snapshot


@dataclass
class PerformanceMetrics:
    """
    Portfolio performance metrics
    
    Implements Requirements 16.9-16.10:
    - Daily P&L tracking (16.9)
    - Benchmark comparison (16.10)
    """
    total_return: Decimal
    total_return_pct: float
    daily_pnl: Decimal
    daily_pnl_pct: float
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    win_rate: float
    num_trades: int
    num_winning_trades: int
    num_losing_trades: int
    avg_win: Decimal
    avg_loss: Decimal
    sharpe_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None
    benchmark_return_pct: Optional[float] = None
    alpha: Optional[float] = None  # Excess return vs benchmark
    beta: Optional[float] = None  # Sensitivity to benchmark
    
    @staticmethod
    def calculate(
        initial_capital: Decimal,
        current_value: Decimal,
        previous_value: Decimal,
        realized_pnl: Decimal,
        unrealized_pnl: Decimal,
        closed_trades: List[Dict],
        benchmark_ticker: str = "SPY"
    ) -> 'PerformanceMetrics':
        """
        Calculate performance metrics
        
        Args:
            initial_capital: Starting capital
            current_value: Current portfolio value
            previous_value: Portfolio value from previous day
            realized_pnl: Total realized P&L
            unrealized_pnl: Total unrealized P&L
            closed_trades: List of closed trades
            benchmark_ticker: Benchmark ticker for comparison (default: SPY)
            
        Returns:
            PerformanceMetrics object
        """
        # Total return
        total_return = current_value - initial_capital
        total_return_pct = float(total_return / initial_capital) if initial_capital > 0 else 0.0
        
        # Daily P&L
        daily_pnl = current_value - previous_value
        daily_pnl_pct = float(daily_pnl / previous_value) if previous_value > 0 else 0.0
        
        # Trade statistics
        num_trades = len(closed_trades)
        winning_trades = [t for t in closed_trades if t['realized_pnl'] > 0]
        losing_trades = [t for t in closed_trades if t['realized_pnl'] < 0]
        
        num_winning_trades = len(winning_trades)
        num_losing_trades = len(losing_trades)
        win_rate = num_winning_trades / num_trades if num_trades > 0 else 0.0
        
        avg_win = Decimal(sum(t['realized_pnl'] for t in winning_trades)) / Decimal(num_winning_trades) if num_winning_trades > 0 else Decimal('0')
        avg_loss = Decimal(sum(t['realized_pnl'] for t in losing_trades)) / Decimal(num_losing_trades) if num_losing_trades > 0 else Decimal('0')
        
        # Benchmark comparison
        benchmark_return_pct = None
        alpha = None
        beta = None
        
        try:
            # Fetch benchmark data
            spy = yf.Ticker(benchmark_ticker)
            hist = spy.history(period="1mo")
            
            if len(hist) >= 2:
                benchmark_start = Decimal(str(hist.iloc[0]['Close']))
                benchmark_end = Decimal(str(hist.iloc[-1]['Close']))
                benchmark_return_pct = float((benchmark_end - benchmark_start) / benchmark_start)
                
                # Calculate alpha (excess return)
                alpha = total_return_pct - benchmark_return_pct
                
                logger.info(
                    "benchmark_comparison",
                    benchmark=benchmark_ticker,
                    portfolio_return=total_return_pct,
                    benchmark_return=benchmark_return_pct,
                    alpha=alpha
                )
        except Exception as e:
            logger.error("benchmark_fetch_failed", error=str(e))
        
        return PerformanceMetrics(
            total_return=total_return,
            total_return_pct=total_return_pct,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            win_rate=win_rate,
            num_trades=num_trades,
            num_winning_trades=num_winning_trades,
            num_losing_trades=num_losing_trades,
            avg_win=avg_win,
            avg_loss=avg_loss,
            benchmark_return_pct=benchmark_return_pct,
            alpha=alpha,
            beta=beta
        )
    
    def compare_to_benchmark(
        self,
        benchmark_ticker: str = "SPY",
        period: str = "1mo"
    ) -> Dict:
        """
        Compare portfolio performance to benchmark
        
        Implements Requirement 16.10: Benchmark comparison
        
        Args:
            benchmark_ticker: Benchmark ticker (default: SPY for S&P 500)
            period: Time period for comparison
            
        Returns:
            Dictionary with comparison metrics
        """
        try:
            benchmark = yf.Ticker(benchmark_ticker)
            hist = benchmark.history(period=period)
            
            if len(hist) < 2:
                return {
                    'error': 'Insufficient benchmark data'
                }
            
            # Calculate benchmark return
            benchmark_start = Decimal(str(hist.iloc[0]['Close']))
            benchmark_end = Decimal(str(hist.iloc[-1]['Close']))
            benchmark_return_pct = float((benchmark_end - benchmark_start) / benchmark_start)
            
            # Calculate excess return (alpha)
            alpha = self.total_return_pct - benchmark_return_pct
            
            # Determine relative performance
            if alpha > 0.02:  # >2% outperformance
                performance = "outperforming"
            elif alpha < -0.02:  # >2% underperformance
                performance = "underperforming"
            else:
                performance = "matching"
            
            return {
                'benchmark_ticker': benchmark_ticker,
                'benchmark_return_pct': benchmark_return_pct,
                'portfolio_return_pct': self.total_return_pct,
                'alpha': alpha,
                'performance': performance,
                'period': period
            }
            
        except Exception as e:
            logger.error("benchmark_comparison_failed", error=str(e))
            return {
                'error': str(e)
            }
