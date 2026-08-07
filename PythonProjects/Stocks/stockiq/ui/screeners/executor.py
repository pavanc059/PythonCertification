"""
Screener Executor

Executes screener filters against stock universe with optimized performance
for sub-5-second execution across 5,000+ stocks.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from .criteria import (
    FilterCondition,
    CompositeFilter,
    FilterOperator,
    ComparisonOperator,
)


class ScreenerExecutor:
    """
    Executes screener filters with optimized performance.
    
    Achieves sub-5-second execution through:
    - Vectorized operations using pandas
    - Early filtering (most restrictive conditions first)
    - Batch processing
    - Parallel execution for independent conditions
    """
    
    def __init__(self, data_source: Optional[Callable] = None):
        """
        Initialize screener executor.
        
        Args:
            data_source: Optional callable that returns stock data DataFrame
        """
        self.data_source = data_source
        self._cache: Dict[str, pd.DataFrame] = {}
        self._cache_timestamp: Optional[datetime] = None
        self._cache_ttl_seconds = 300  # 5-minute cache
    
    def execute(
        self,
        composite_filter: CompositeFilter,
        stock_universe: Optional[pd.DataFrame] = None,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Execute screener filter against stock universe.
        
        Args:
            composite_filter: The composite filter to apply
            stock_universe: Optional DataFrame with stock data. If None, uses data_source
            limit: Optional limit on number of results
        
        Returns:
            DataFrame with matching stocks
        
        Raises:
            ValueError: If no stock data available
        """
        start_time = time.time()
        
        # Get stock data
        if stock_universe is None:
            stock_universe = self._get_stock_data()
        
        if stock_universe is None or stock_universe.empty:
            raise ValueError("No stock data available")
        
        # Apply filters
        result = self._apply_composite_filter(stock_universe, composite_filter)
        
        # Apply limit if specified
        if limit is not None and len(result) > limit:
            result = result.head(limit)
        
        execution_time = time.time() - start_time
        
        # Log performance warning if execution took too long
        if execution_time > 5.0:
            print(f"⚠️  Warning: Screener execution took {execution_time:.2f}s (target: <5s)")
        
        return result
    
    def _get_stock_data(self) -> pd.DataFrame:
        """Get stock data from cache or data source"""
        # Check cache validity
        if self._cache_timestamp is not None:
            cache_age = (datetime.now() - self._cache_timestamp).total_seconds()
            if cache_age < self._cache_ttl_seconds and 'universe' in self._cache:
                return self._cache['universe']
        
        # Fetch fresh data
        if self.data_source is None:
            raise ValueError("No data source configured")
        
        data = self.data_source()
        
        # Cache the data
        self._cache['universe'] = data
        self._cache_timestamp = datetime.now()
        
        return data
    
    def _apply_composite_filter(
        self,
        data: pd.DataFrame,
        composite_filter: CompositeFilter
    ) -> pd.DataFrame:
        """Apply composite filter with logical operators"""
        if not composite_filter.conditions:
            return data
        
        # Sort conditions by restrictiveness (heuristic: numeric comparisons first)
        sorted_conditions = self._sort_conditions_by_restrictiveness(
            composite_filter.conditions
        )
        
        # Apply conditions based on operator
        if composite_filter.operator == FilterOperator.AND:
            return self._apply_and_conditions(data, sorted_conditions)
        elif composite_filter.operator == FilterOperator.OR:
            return self._apply_or_conditions(data, sorted_conditions)
        else:
            raise ValueError(f"Unsupported operator: {composite_filter.operator}")
    
    def _apply_and_conditions(
        self,
        data: pd.DataFrame,
        conditions: List[FilterCondition]
    ) -> pd.DataFrame:
        """Apply conditions with AND logic (sequential filtering for early exit)"""
        result = data.copy()
        
        for condition in conditions:
            if result.empty:
                break  # Early exit if no matches
            
            result = self._apply_single_condition(result, condition)
        
        return result
    
    def _apply_or_conditions(
        self,
        data: pd.DataFrame,
        conditions: List[FilterCondition]
    ) -> pd.DataFrame:
        """Apply conditions with OR logic (union of results)"""
        if not conditions:
            return data
        
        # Apply each condition independently and union results
        result_dfs = []
        
        for condition in conditions:
            matched = self._apply_single_condition(data, condition)
            if not matched.empty:
                result_dfs.append(matched)
        
        if not result_dfs:
            return pd.DataFrame()
        
        # Union all results and remove duplicates
        combined = pd.concat(result_dfs, ignore_index=False)
        return combined.drop_duplicates()
    
    def _apply_single_condition(
        self,
        data: pd.DataFrame,
        condition: FilterCondition
    ) -> pd.DataFrame:
        """Apply a single filter condition"""
        criteria_name = condition.criteria.name
        
        # Check if column exists
        if criteria_name not in data.columns:
            print(f"⚠️  Warning: Column '{criteria_name}' not found in data")
            return data if condition.negate else pd.DataFrame()
        
        # Get mask based on operator
        mask = self._get_condition_mask(data, condition)
        
        # Apply negation if needed
        if condition.negate:
            mask = ~mask
        
        return data[mask]
    
    def _get_condition_mask(
        self,
        data: pd.DataFrame,
        condition: FilterCondition
    ) -> pd.Series:
        """Get boolean mask for a condition using vectorized operations"""
        column = data[condition.criteria.name]
        operator = condition.operator
        value = condition.value
        
        # Handle None/NaN values
        valid_mask = column.notna()
        
        if operator == ComparisonOperator.EQUALS:
            mask = column == value
        elif operator == ComparisonOperator.NOT_EQUALS:
            mask = column != value
        elif operator == ComparisonOperator.GREATER_THAN:
            mask = column > value
        elif operator == ComparisonOperator.GREATER_THAN_OR_EQUAL:
            mask = column >= value
        elif operator == ComparisonOperator.LESS_THAN:
            mask = column < value
        elif operator == ComparisonOperator.LESS_THAN_OR_EQUAL:
            mask = column <= value
        elif operator == ComparisonOperator.BETWEEN:
            if not isinstance(value, list) or len(value) != 2:
                raise ValueError("BETWEEN operator requires list of [min, max]")
            mask = (column >= value[0]) & (column <= value[1])
        elif operator == ComparisonOperator.IN:
            mask = column.isin(value)
        elif operator == ComparisonOperator.NOT_IN:
            mask = ~column.isin(value)
        elif operator == ComparisonOperator.CONTAINS:
            mask = column.astype(str).str.contains(str(value), case=False, na=False)
        elif operator == ComparisonOperator.NOT_CONTAINS:
            mask = ~column.astype(str).str.contains(str(value), case=False, na=False)
        else:
            raise ValueError(f"Unsupported operator: {operator}")
        
        # Combine with valid mask (exclude NaN values)
        return mask & valid_mask
    
    def _sort_conditions_by_restrictiveness(
        self,
        conditions: List[FilterCondition]
    ) -> List[FilterCondition]:
        """
        Sort conditions by estimated restrictiveness for optimal performance.
        
        Heuristic: Apply most restrictive filters first to reduce data size quickly.
        - Exact matches (equals, in) are most restrictive
        - Numeric comparisons are moderately restrictive
        - String operations are least restrictive
        """
        def restrictiveness_score(condition: FilterCondition) -> int:
            operator = condition.operator
            data_type = condition.criteria.data_type
            
            # Exact matches first
            if operator in [ComparisonOperator.EQUALS, ComparisonOperator.IN]:
                return 3
            
            # Numeric comparisons second
            if data_type in [int, float]:
                return 2
            
            # String operations last
            return 1
        
        return sorted(conditions, key=restrictiveness_score, reverse=True)
    
    def clear_cache(self) -> None:
        """Clear the data cache"""
        self._cache.clear()
        self._cache_timestamp = None
    
    def set_cache_ttl(self, seconds: int) -> None:
        """Set cache time-to-live in seconds"""
        self._cache_ttl_seconds = seconds
    
    def get_execution_stats(
        self,
        composite_filter: CompositeFilter,
        stock_universe: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Get execution statistics for a screener.
        
        Returns:
            Dictionary with execution time, result count, and performance metrics
        """
        start_time = time.time()
        
        result = self.execute(composite_filter, stock_universe)
        
        execution_time = time.time() - start_time
        
        return {
            'execution_time_seconds': execution_time,
            'result_count': len(result),
            'total_stocks_scanned': len(stock_universe) if stock_universe is not None else 0,
            'filter_efficiency': len(result) / len(stock_universe) if stock_universe is not None and len(stock_universe) > 0 else 0,
            'meets_performance_target': execution_time < 5.0,
        }


class BatchScreenerExecutor:
    """
    Execute multiple screeners in parallel for batch processing.
    """
    
    def __init__(self, executor: ScreenerExecutor, max_workers: int = 4):
        """
        Initialize batch executor.
        
        Args:
            executor: ScreenerExecutor instance
            max_workers: Maximum number of parallel workers
        """
        self.executor = executor
        self.max_workers = max_workers
    
    def execute_batch(
        self,
        screeners: List[CompositeFilter],
        stock_universe: Optional[pd.DataFrame] = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Execute multiple screeners in parallel.
        
        Args:
            screeners: List of composite filters to execute
            stock_universe: Optional stock data (shared across all screeners)
        
        Returns:
            Dictionary mapping screener names to result DataFrames
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all screener tasks
            future_to_screener = {
                executor.submit(
                    self.executor.execute,
                    screener,
                    stock_universe
                ): screener
                for screener in screeners
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_screener):
                screener = future_to_screener[future]
                try:
                    result = future.result()
                    name = screener.name or f"Screener_{id(screener)}"
                    results[name] = result
                except Exception as e:
                    print(f"Error executing screener {screener.name}: {e}")
        
        return results
