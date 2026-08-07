"""
Top movers calculation (gainers and losers).
"""

from decimal import Decimal
from typing import List, Dict
from datetime import date
import pandas as pd
import structlog

from ..models import TopMover, Stock, OHLCV
from ...infrastructure.cache import get_cache, CacheKeyPatterns
from ...infrastructure.database import get_db_context
from ...infrastructure.models import Stock as StockModel, TopMover as TopMoverModel

logger = structlog.get_logger(__name__)


class TopMoversCalculator:
    """Calculate top movers (gainers and losers) from market data."""
    
    def __init__(self):
        self.cache = get_cache()
    
    @staticmethod
    def calculate_percentage_change(open_price: Decimal, close_price: Decimal) -> Decimal:
        """
        Calculate percentage change (Property 3).
        
        Args:
            open_price: Opening price
            close_price: Closing price
        
        Returns:
            Percentage change
        
        Raises:
            ValueError: If open price is zero
        """
        if open_price == 0:
            raise ValueError("Open price cannot be zero")
        
        return ((close_price - open_price) / open_price) * 100
    
    def identify_top_gainers(
        self,
        stocks_data: List[Dict],
        limit: int = 20
    ) -> List[TopMover]:
        """
        Identify top gaining stocks (Property 1).
        
        Property 1: For any set of stock price data with percentage changes,
        when identifying the top 20 gainers, the system SHALL return exactly
        20 stocks (or fewer if less than 20 available) sorted in descending
        order by percentage change.
        
        Args:
            stocks_data: List of stock data dictionaries
            limit: Maximum number of gainers to return
        
        Returns:
            List of TopMover objects sorted by percentage change (descending)
        """
        if not stocks_data:
            return []
        
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(stocks_data)
        
        # Filter by market cap and volume (Properties 4, 5)
        df = df[df['market_cap'] >= 100_000_000]  # Property 4: >= $100M
        df = df[df['avg_volume'] >= 100_000]      # Property 5: >= 100k shares
        
        # Sort by percentage change descending
        df = df.sort_values('price_change_pct', ascending=False)
        
        # Take top N
        df = df.head(limit)
        
        # Convert to TopMover objects
        gainers = []
        for idx, row in df.iterrows():
            mover = TopMover(
                ticker=row['ticker'],
                name=row['name'],
                price_change_pct=float(row['price_change_pct']),
                price_change_abs=Decimal(str(row['price_change_abs'])),
                current_price=Decimal(str(row['current_price'])),
                volume=int(row['volume']),
                avg_volume=int(row['avg_volume']),
                market_cap=int(row['market_cap']),
                sector=row['sector'],
                is_gainer=True
            )
            gainers.append(mover)
        
        # Verify Property 1: sorted in descending order
        for i in range(len(gainers) - 1):
            assert gainers[i].price_change_pct >= gainers[i + 1].price_change_pct, \
                "Gainers must be sorted in descending order"
        
        logger.info("top_gainers_identified", count=len(gainers))
        return gainers
    
    def identify_top_losers(
        self,
        stocks_data: List[Dict],
        limit: int = 20
    ) -> List[TopMover]:
        """
        Identify top losing stocks (Property 2).
        
        Property 2: For any set of stock price data with percentage changes,
        when identifying the top 20 losers, the system SHALL return exactly
        20 stocks (or fewer if less than 20 available) sorted in ascending
        order by percentage change.
        
        Args:
            stocks_data: List of stock data dictionaries
            limit: Maximum number of losers to return
        
        Returns:
            List of TopMover objects sorted by percentage change (ascending)
        """
        if not stocks_data:
            return []
        
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(stocks_data)
        
        # Filter by market cap and volume (Properties 4, 5)
        df = df[df['market_cap'] >= 100_000_000]  # Property 4: >= $100M
        df = df[df['avg_volume'] >= 100_000]      # Property 5: >= 100k shares
        
        # Sort by percentage change ascending
        df = df.sort_values('price_change_pct', ascending=True)
        
        # Take top N
        df = df.head(limit)
        
        # Convert to TopMover objects
        losers = []
        for idx, row in df.iterrows():
            mover = TopMover(
                ticker=row['ticker'],
                name=row['name'],
                price_change_pct=float(row['price_change_pct']),
                price_change_abs=Decimal(str(row['price_change_abs'])),
                current_price=Decimal(str(row['current_price'])),
                volume=int(row['volume']),
                avg_volume=int(row['avg_volume']),
                market_cap=int(row['market_cap']),
                sector=row['sector'],
                is_gainer=False
            )
            losers.append(mover)
        
        # Verify Property 2: sorted in ascending order
        for i in range(len(losers) - 1):
            assert losers[i].price_change_pct <= losers[i + 1].price_change_pct, \
                "Losers must be sorted in ascending order"
        
        logger.info("top_losers_identified", count=len(losers))
        return losers
    
    def filter_by_market_cap(
        self,
        stocks: pd.DataFrame,
        min_cap: int = 100_000_000
    ) -> pd.DataFrame:
        """
        Filter stocks by market capitalization (Property 4).
        
        Property 4: For any set of stocks processed for top movers,
        all returned stocks SHALL have a market capitalization greater
        than or equal to $100 million.
        
        Args:
            stocks: DataFrame with stock data
            min_cap: Minimum market cap (default: $100M)
        
        Returns:
            Filtered DataFrame
        """
        if stocks.empty:
            return stocks
        
        filtered = stocks[stocks['market_cap'] >= min_cap].copy()
        
        # Verify Property 4: all stocks have market_cap >= min_cap
        if not filtered.empty:
            assert (filtered['market_cap'] >= min_cap).all(), \
                f"All stocks must have market_cap >= {min_cap}"
        
        logger.info(
            "stocks_filtered_by_market_cap",
            before=len(stocks),
            after=len(filtered),
            min_cap=min_cap
        )
        return filtered
    
    def filter_by_volume(
        self,
        stocks: pd.DataFrame,
        min_volume: int = 100_000
    ) -> pd.DataFrame:
        """
        Filter stocks by average daily volume (Property 5).
        
        Property 5: For any set of stocks processed for top movers,
        all returned stocks SHALL have an average daily volume greater
        than or equal to 100,000 shares.
        
        Args:
            stocks: DataFrame with stock data
            min_volume: Minimum average volume (default: 100k shares)
        
        Returns:
            Filtered DataFrame
        """
        if stocks.empty:
            return stocks
        
        filtered = stocks[stocks['avg_volume'] >= min_volume].copy()
        
        # Verify Property 5: all stocks have avg_volume >= min_volume
        if not filtered.empty:
            assert (filtered['avg_volume'] >= min_volume).all(), \
                f"All stocks must have avg_volume >= {min_volume}"
        
        logger.info(
            "stocks_filtered_by_volume",
            before=len(stocks),
            after=len(filtered),
            min_volume=min_volume
        )
        return filtered
    
    def detect_unusual_volume(self, stock: Stock) -> bool:
        """
        Detect unusual volume for a stock (Property 7).
        
        Property 7: For any stock with current volume and average volume,
        the stock SHALL be flagged as having unusual volume if and only if
        current_volume > 3 * average_volume.
        
        Args:
            stock: Stock object with volume information
        
        Returns:
            True if unusual volume detected, False otherwise
        """
        if not hasattr(stock, 'volume') or not hasattr(stock, 'avg_volume'):
            return False
        
        if stock.avg_volume is None or stock.avg_volume == 0:
            return False
        
        # Property 7: unusual_volume iff current_volume > 3 * avg_volume
        volume_ratio = stock.volume / stock.avg_volume
        is_unusual = volume_ratio > 3.0
        
        if is_unusual:
            logger.info(
                "unusual_volume_detected",
                ticker=stock.ticker,
                volume=stock.volume,
                avg_volume=stock.avg_volume,
                ratio=volume_ratio
            )
        
        return is_unusual
    
    def calculate_sector_performance(
        self,
        stocks: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calculate sector performance (Property 6).
        
        Property 6: For any set of stocks grouped by sector with individual
        returns, the calculated sector performance SHALL equal the weighted
        average return of all stocks in that sector, and sectors SHALL be
        ranked in descending order by performance.
        
        Args:
            stocks: DataFrame with stock data including 'sector', 
                   'price_change_pct', and 'market_cap' columns
        
        Returns:
            Dictionary mapping sector to performance percentage,
            sorted in descending order by performance
        """
        if stocks.empty:
            return {}
        
        # Ensure required columns exist
        required_cols = ['sector', 'price_change_pct', 'market_cap']
        missing_cols = [col for col in required_cols if col not in stocks.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Group by sector and calculate weighted average
        sector_performance = {}
        for sector in stocks['sector'].unique():
            if pd.isna(sector):
                continue
                
            sector_df = stocks[stocks['sector'] == sector]
            
            # Weighted average by market cap
            total_market_cap = sector_df['market_cap'].sum()
            if total_market_cap == 0:
                continue
            
            weighted_return = (
                (sector_df['price_change_pct'] * sector_df['market_cap']).sum()
                / total_market_cap
            )
            
            sector_performance[sector] = float(weighted_return)
        
        # Sort by performance descending (Property 6)
        sector_performance = dict(
            sorted(sector_performance.items(), key=lambda x: x[1], reverse=True)
        )
        
        # Verify Property 6: sectors are ranked in descending order
        if len(sector_performance) > 1:
            values = list(sector_performance.values())
            for i in range(len(values) - 1):
                assert values[i] >= values[i + 1], \
                    "Sectors must be ranked in descending order by performance"
        
        logger.info("sector_performance_calculated", sectors=len(sector_performance))
        return sector_performance
    
    def save_to_database(
        self,
        movers: List[TopMover],
        trading_date: date
    ):
        """
        Save top movers to database.
        
        Args:
            movers: List of TopMover objects
            trading_date: Trading date
        """
        try:
            with get_db_context() as db:
                for rank, mover in enumerate(movers, start=1):
                    # Get stock_id
                    stock = db.query(StockModel).filter(
                        StockModel.ticker == mover.ticker
                    ).first()
                    
                    if not stock:
                        logger.warning("stock_not_found", ticker=mover.ticker)
                        continue
                    
                    # Create top mover record
                    top_mover = TopMoverModel(
                        stock_id=stock.id,
                        date=trading_date,
                        price_change_pct=mover.price_change_pct,
                        price_change_abs=mover.price_change_abs,
                        volume=mover.volume,
                        volume_ratio=mover.volume_ratio(),
                        is_gainer=mover.is_gainer,
                        rank=rank,
                        has_unusual_volume=mover.has_unusual_volume()
                    )
                    
                    db.add(top_mover)
                
                db.commit()
                logger.info(
                    "top_movers_saved",
                    count=len(movers),
                    date=trading_date
                )
                
        except Exception as e:
            logger.error("save_top_movers_failed", error=str(e))
            raise
    
    def cache_top_movers(
        self,
        gainers: List[TopMover],
        losers: List[TopMover],
        trading_date: date
    ):
        """
        Cache top movers for quick access.
        
        Args:
            gainers: List of top gainers
            losers: List of top losers
            trading_date: Trading date
        """
        # Cache gainers
        gainers_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.MOVERS_GAINERS,
            date=trading_date.isoformat()
        )
        self.cache.set(gainers_key, gainers, ttl=86400)  # 24 hours
        
        # Cache losers
        losers_key = CacheKeyPatterns.format_key(
            CacheKeyPatterns.MOVERS_LOSERS,
            date=trading_date.isoformat()
        )
        self.cache.set(losers_key, losers, ttl=86400)  # 24 hours
        
        logger.info(
            "top_movers_cached",
            gainers=len(gainers),
            losers=len(losers),
            date=trading_date
        )
