"""
Screener Builder

Provides a fluent API for building composite screeners with multiple conditions.
"""

from typing import Any, List, Optional, Union
from .criteria import (
    FilterCriteria,
    FilterCondition,
    CompositeFilter,
    FilterOperator,
    ComparisonOperator,
    get_criteria_by_name,
)


class ScreenerBuilder:
    """
    Fluent API for building stock screeners.
    
    Example:
        screener = (ScreenerBuilder()
            .with_name("Growth Stocks")
            .where("market_cap").greater_than(10_000_000_000)
            .and_where("revenue_growth").greater_than(20)
            .and_where("pe_ratio").less_than(30)
            .build())
    """
    
    def __init__(self):
        self._conditions: List[FilterCondition] = []
        self._operator: FilterOperator = FilterOperator.AND
        self._name: Optional[str] = None
        self._description: Optional[str] = None
        self._current_criteria: Optional[FilterCriteria] = None
    
    def with_name(self, name: str) -> 'ScreenerBuilder':
        """Set the screener name"""
        self._name = name
        return self
    
    def with_description(self, description: str) -> 'ScreenerBuilder':
        """Set the screener description"""
        self._description = description
        return self
    
    def with_operator(self, operator: FilterOperator) -> 'ScreenerBuilder':
        """Set the logical operator (AND/OR)"""
        self._operator = operator
        return self
    
    def where(self, criteria_name: str) -> 'ScreenerBuilder':
        """Start a new filter condition"""
        criteria = get_criteria_by_name(criteria_name)
        if criteria is None:
            raise ValueError(f"Unknown criteria: {criteria_name}")
        self._current_criteria = criteria
        return self
    
    def and_where(self, criteria_name: str) -> 'ScreenerBuilder':
        """Add an AND condition (alias for where)"""
        return self.where(criteria_name)
    
    def or_where(self, criteria_name: str) -> 'ScreenerBuilder':
        """Add an OR condition"""
        self.with_operator(FilterOperator.OR)
        return self.where(criteria_name)
    
    def equals(self, value: Any) -> 'ScreenerBuilder':
        """Add equals condition"""
        return self._add_condition(ComparisonOperator.EQUALS, value)
    
    def not_equals(self, value: Any) -> 'ScreenerBuilder':
        """Add not equals condition"""
        return self._add_condition(ComparisonOperator.NOT_EQUALS, value)
    
    def greater_than(self, value: Union[int, float]) -> 'ScreenerBuilder':
        """Add greater than condition"""
        return self._add_condition(ComparisonOperator.GREATER_THAN, value)
    
    def greater_than_or_equal(self, value: Union[int, float]) -> 'ScreenerBuilder':
        """Add greater than or equal condition"""
        return self._add_condition(ComparisonOperator.GREATER_THAN_OR_EQUAL, value)
    
    def less_than(self, value: Union[int, float]) -> 'ScreenerBuilder':
        """Add less than condition"""
        return self._add_condition(ComparisonOperator.LESS_THAN, value)
    
    def less_than_or_equal(self, value: Union[int, float]) -> 'ScreenerBuilder':
        """Add less than or equal condition"""
        return self._add_condition(ComparisonOperator.LESS_THAN_OR_EQUAL, value)
    
    def between(self, min_value: Union[int, float], max_value: Union[int, float]) -> 'ScreenerBuilder':
        """Add between condition"""
        return self._add_condition(ComparisonOperator.BETWEEN, [min_value, max_value])
    
    def in_list(self, values: List[Any]) -> 'ScreenerBuilder':
        """Add IN condition"""
        return self._add_condition(ComparisonOperator.IN, values)
    
    def not_in_list(self, values: List[Any]) -> 'ScreenerBuilder':
        """Add NOT IN condition"""
        return self._add_condition(ComparisonOperator.NOT_IN, values)
    
    def contains(self, value: str) -> 'ScreenerBuilder':
        """Add contains condition (for string fields)"""
        return self._add_condition(ComparisonOperator.CONTAINS, value)
    
    def not_contains(self, value: str) -> 'ScreenerBuilder':
        """Add not contains condition (for string fields)"""
        return self._add_condition(ComparisonOperator.NOT_CONTAINS, value)
    
    def negate(self) -> 'ScreenerBuilder':
        """Negate the next condition"""
        if self._conditions:
            self._conditions[-1].negate = True
        return self
    
    def _add_condition(self, operator: ComparisonOperator, value: Any) -> 'ScreenerBuilder':
        """Add a condition to the screener"""
        if self._current_criteria is None:
            raise ValueError("Must call where() before adding a condition")
        
        # Validate operator is allowed for this criteria
        if operator not in self._current_criteria.valid_operators:
            raise ValueError(
                f"Operator {operator.value} not valid for {self._current_criteria.name}. "
                f"Valid operators: {[op.value for op in self._current_criteria.valid_operators]}"
            )
        
        # Validate value type
        if not self._current_criteria.validate_value(value):
            raise ValueError(
                f"Invalid value type for {self._current_criteria.name}. "
                f"Expected {self._current_criteria.data_type.__name__}"
            )
        
        condition = FilterCondition(
            criteria=self._current_criteria,
            operator=operator,
            value=value
        )
        self._conditions.append(condition)
        self._current_criteria = None
        return self
    
    def build(self) -> CompositeFilter:
        """Build the composite filter"""
        if not self._conditions:
            raise ValueError("Cannot build screener with no conditions")
        
        return CompositeFilter(
            conditions=self._conditions,
            operator=self._operator,
            name=self._name,
            description=self._description
        )
    
    def reset(self) -> 'ScreenerBuilder':
        """Reset the builder to start fresh"""
        self._conditions = []
        self._operator = FilterOperator.AND
        self._name = None
        self._description = None
        self._current_criteria = None
        return self


def create_value_screener() -> CompositeFilter:
    """Pre-built screener: Value stocks"""
    return (ScreenerBuilder()
        .with_name("Value Stocks")
        .with_description("Stocks with strong value characteristics")
        .where("pe_ratio").less_than(15)
        .and_where("pb_ratio").less_than(2)
        .and_where("dividend_yield").greater_than(2)
        .and_where("market_cap").greater_than(1_000_000_000)
        .build())


def create_growth_screener() -> CompositeFilter:
    """Pre-built screener: Growth stocks"""
    return (ScreenerBuilder()
        .with_name("Growth Stocks")
        .with_description("Stocks with strong growth characteristics")
        .where("revenue_growth").greater_than(20)
        .and_where("earnings_growth").greater_than(15)
        .and_where("market_cap").greater_than(5_000_000_000)
        .build())


def create_momentum_screener() -> CompositeFilter:
    """Pre-built screener: Momentum stocks"""
    return (ScreenerBuilder()
        .with_name("Momentum Stocks")
        .with_description("Stocks with strong price momentum")
        .where("return_1m").greater_than(10)
        .and_where("rsi").between(50, 70)
        .and_where("volume_ratio").greater_than(1.5)
        .and_where("market_cap").greater_than(500_000_000)
        .build())


def create_dividend_screener() -> CompositeFilter:
    """Pre-built screener: Dividend stocks"""
    return (ScreenerBuilder()
        .with_name("Dividend Champions")
        .with_description("High-quality dividend stocks")
        .where("dividend_yield").greater_than(3)
        .and_where("debt_to_equity").less_than(1)
        .and_where("market_cap").greater_than(2_000_000_000)
        .build())


def create_penny_stock_screener() -> CompositeFilter:
    """Pre-built screener: Penny stocks with momentum"""
    return (ScreenerBuilder()
        .with_name("Penny Stock Momentum")
        .with_description("Penny stocks under $5 with strong momentum")
        .where("price").less_than(5)
        .and_where("price_change_pct").greater_than(10)
        .and_where("volume_ratio").greater_than(2)
        .and_where("avg_volume").greater_than(50_000)
        .build())


# Pre-built screeners
PREBUILT_SCREENERS = {
    "value": create_value_screener,
    "growth": create_growth_screener,
    "momentum": create_momentum_screener,
    "dividend": create_dividend_screener,
    "penny": create_penny_stock_screener,
}


def get_prebuilt_screener(name: str) -> Optional[CompositeFilter]:
    """Get a pre-built screener by name"""
    factory = PREBUILT_SCREENERS.get(name)
    return factory() if factory else None


def list_prebuilt_screeners() -> List[str]:
    """List all available pre-built screeners"""
    return list(PREBUILT_SCREENERS.keys())
