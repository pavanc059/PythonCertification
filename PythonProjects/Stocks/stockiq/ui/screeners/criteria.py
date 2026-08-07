"""
Filter Criteria Definitions

Defines all available filter criteria, operators, and data types for stock screening.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Any, List, Optional, Union
from decimal import Decimal


class FilterOperator(Enum):
    """Logical operators for combining filter criteria"""
    AND = "AND"
    OR = "OR"
    NOT = "NOT"


class ComparisonOperator(Enum):
    """Comparison operators for filter conditions"""
    EQUALS = "="
    NOT_EQUALS = "!="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    BETWEEN = "BETWEEN"
    IN = "IN"
    NOT_IN = "NOT IN"
    CONTAINS = "CONTAINS"
    NOT_CONTAINS = "NOT CONTAINS"


class CriteriaType(Enum):
    """Categories of filter criteria"""
    PRICE = "price"
    VOLUME = "volume"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    PERFORMANCE = "performance"
    VALUATION = "valuation"
    GROWTH = "growth"
    RISK = "risk"
    MARKET = "market"


@dataclass
class FilterCriteria:
    """
    Represents a single filter criterion for stock screening.
    
    Attributes:
        name: Unique identifier for the criterion
        display_name: Human-readable name
        category: Criteria category
        data_type: Expected data type (float, int, str, bool)
        description: Explanation of the criterion
        valid_operators: Allowed comparison operators
        default_operator: Default comparison operator
        unit: Optional unit of measurement (%, $, etc.)
    """
    name: str
    display_name: str
    category: CriteriaType
    data_type: type
    description: str
    valid_operators: List[ComparisonOperator]
    default_operator: ComparisonOperator
    unit: Optional[str] = None
    
    def validate_value(self, value: Any) -> bool:
        """Validate that value matches expected data type"""
        try:
            # Handle lists (for BETWEEN, IN, NOT_IN operators)
            if isinstance(value, list):
                return all(self._validate_single_value(v) for v in value)
            else:
                return self._validate_single_value(value)
        except (ValueError, TypeError):
            return False
    
    def _validate_single_value(self, value: Any) -> bool:
        """Validate a single value"""
        if self.data_type == float:
            float(value)
        elif self.data_type == int:
            int(value)
        elif self.data_type == str:
            str(value)
        elif self.data_type == bool:
            bool(value)
        return True


@dataclass
class FilterCondition:
    """
    Represents a single filter condition to apply.
    
    Attributes:
        criteria: The filter criterion
        operator: Comparison operator
        value: Filter value(s)
        negate: Whether to negate the condition (for NOT operator)
    """
    criteria: FilterCriteria
    operator: ComparisonOperator
    value: Union[Any, List[Any]]
    negate: bool = False
    
    def __repr__(self) -> str:
        """String representation of the condition"""
        neg = "NOT " if self.negate else ""
        if self.operator == ComparisonOperator.BETWEEN:
            return f"{neg}{self.criteria.display_name} {self.operator.value} {self.value[0]} AND {self.value[1]}"
        elif self.operator in [ComparisonOperator.IN, ComparisonOperator.NOT_IN]:
            return f"{neg}{self.criteria.display_name} {self.operator.value} ({', '.join(map(str, self.value))})"
        else:
            return f"{neg}{self.criteria.display_name} {self.operator.value} {self.value}"


@dataclass
class CompositeFilter:
    """
    Represents a composite filter with multiple conditions and logical operators.
    
    Attributes:
        conditions: List of filter conditions
        operator: Logical operator (AND/OR) to combine conditions
        name: Optional name for saved screeners
        description: Optional description
    """
    conditions: List[FilterCondition]
    operator: FilterOperator = FilterOperator.AND
    name: Optional[str] = None
    description: Optional[str] = None
    
    def add_condition(self, condition: FilterCondition) -> None:
        """Add a filter condition to the composite filter"""
        self.conditions.append(condition)
    
    def remove_condition(self, index: int) -> None:
        """Remove a filter condition by index"""
        if 0 <= index < len(self.conditions):
            self.conditions.pop(index)
    
    def __repr__(self) -> str:
        """String representation of the composite filter"""
        if not self.conditions:
            return "Empty Filter"
        
        op_str = f" {self.operator.value} "
        conditions_str = op_str.join([str(c) for c in self.conditions])
        
        if self.name:
            return f"{self.name}: {conditions_str}"
        return conditions_str


# Define all available filter criteria (20+ criteria as per Requirement 17.7)
AVAILABLE_CRITERIA = {
    # Price Criteria
    "price": FilterCriteria(
        name="price",
        display_name="Price",
        category=CriteriaType.PRICE,
        data_type=float,
        description="Current stock price",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.GREATER_THAN_OR_EQUAL,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.LESS_THAN_OR_EQUAL,
            ComparisonOperator.BETWEEN,
        ],
        default_operator=ComparisonOperator.GREATER_THAN,
        unit="$"
    ),
    
    "price_change_pct": FilterCriteria(
        name="price_change_pct",
        display_name="Price Change %",
        category=CriteriaType.PERFORMANCE,
        data_type=float,
        description="Percentage price change (1-day)",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.GREATER_THAN_OR_EQUAL,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.LESS_THAN_OR_EQUAL,
            ComparisonOperator.BETWEEN,
        ],
        default_operator=ComparisonOperator.GREATER_THAN,
        unit="%"
    ),
    
    # Volume Criteria
    "volume": FilterCriteria(
        name="volume",
        display_name="Volume",
        category=CriteriaType.VOLUME,
        data_type=int,
        description="Current trading volume",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.GREATER_THAN_OR_EQUAL,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.LESS_THAN_OR_EQUAL,
        ],
        default_operator=ComparisonOperator.GREATER_THAN
    ),
    
    "avg_volume": FilterCriteria(
        name="avg_volume",
        display_name="Average Volume",
        category=CriteriaType.VOLUME,
        data_type=int,
        description="Average daily trading volume (30-day)",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.GREATER_THAN_OR_EQUAL,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.LESS_THAN_OR_EQUAL,
        ],
        default_operator=ComparisonOperator.GREATER_THAN
    ),
    
    "volume_ratio": FilterCriteria(
        name="volume_ratio",
        display_name="Volume Ratio",
        category=CriteriaType.VOLUME,
        data_type=float,
        description="Current volume / Average volume",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.GREATER_THAN_OR_EQUAL,
        ],
        default_operator=ComparisonOperator.GREATER_THAN
    ),
    
    # Technical Indicators
    "rsi": FilterCriteria(
        name="rsi",
        display_name="RSI (14)",
        category=CriteriaType.TECHNICAL,
        data_type=float,
        description="Relative Strength Index",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.BETWEEN,
        ],
        default_operator=ComparisonOperator.LESS_THAN
    ),
    
    "macd_signal": FilterCriteria(
        name="macd_signal",
        display_name="MACD Signal",
        category=CriteriaType.TECHNICAL,
        data_type=str,
        description="MACD signal (bullish/bearish)",
        valid_operators=[
            ComparisonOperator.EQUALS,
            ComparisonOperator.IN,
        ],
        default_operator=ComparisonOperator.EQUALS
    ),
    
    "sma_20": FilterCriteria(
        name="sma_20",
        display_name="Price vs SMA 20",
        category=CriteriaType.TECHNICAL,
        data_type=str,
        description="Price relative to 20-day SMA",
        valid_operators=[
            ComparisonOperator.EQUALS,
        ],
        default_operator=ComparisonOperator.EQUALS
    ),
    
    "sma_50": FilterCriteria(
        name="sma_50",
        display_name="Price vs SMA 50",
        category=CriteriaType.TECHNICAL,
        data_type=str,
        description="Price relative to 50-day SMA",
        valid_operators=[
            ComparisonOperator.EQUALS,
        ],
        default_operator=ComparisonOperator.EQUALS
    ),
    
    # Fundamental Criteria
    "market_cap": FilterCriteria(
        name="market_cap",
        display_name="Market Cap",
        category=CriteriaType.FUNDAMENTAL,
        data_type=float,
        description="Market capitalization",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.GREATER_THAN_OR_EQUAL,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.LESS_THAN_OR_EQUAL,
            ComparisonOperator.BETWEEN,
        ],
        default_operator=ComparisonOperator.GREATER_THAN,
        unit="$"
    ),
    
    "pe_ratio": FilterCriteria(
        name="pe_ratio",
        display_name="P/E Ratio",
        category=CriteriaType.VALUATION,
        data_type=float,
        description="Price-to-Earnings ratio",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.BETWEEN,
        ],
        default_operator=ComparisonOperator.LESS_THAN
    ),
    
    "pb_ratio": FilterCriteria(
        name="pb_ratio",
        display_name="P/B Ratio",
        category=CriteriaType.VALUATION,
        data_type=float,
        description="Price-to-Book ratio",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.BETWEEN,
        ],
        default_operator=ComparisonOperator.LESS_THAN
    ),
    
    "dividend_yield": FilterCriteria(
        name="dividend_yield",
        display_name="Dividend Yield",
        category=CriteriaType.FUNDAMENTAL,
        data_type=float,
        description="Dividend yield percentage",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.GREATER_THAN_OR_EQUAL,
        ],
        default_operator=ComparisonOperator.GREATER_THAN,
        unit="%"
    ),
    
    "debt_to_equity": FilterCriteria(
        name="debt_to_equity",
        display_name="Debt-to-Equity",
        category=CriteriaType.RISK,
        data_type=float,
        description="Debt-to-Equity ratio",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.BETWEEN,
        ],
        default_operator=ComparisonOperator.LESS_THAN
    ),
    
    # Growth Criteria
    "revenue_growth": FilterCriteria(
        name="revenue_growth",
        display_name="Revenue Growth",
        category=CriteriaType.GROWTH,
        data_type=float,
        description="Year-over-year revenue growth",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.GREATER_THAN_OR_EQUAL,
        ],
        default_operator=ComparisonOperator.GREATER_THAN,
        unit="%"
    ),
    
    "earnings_growth": FilterCriteria(
        name="earnings_growth",
        display_name="Earnings Growth",
        category=CriteriaType.GROWTH,
        data_type=float,
        description="Year-over-year earnings growth",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.GREATER_THAN_OR_EQUAL,
        ],
        default_operator=ComparisonOperator.GREATER_THAN,
        unit="%"
    ),
    
    # Sentiment Criteria
    "sentiment_score": FilterCriteria(
        name="sentiment_score",
        display_name="Sentiment Score",
        category=CriteriaType.SENTIMENT,
        data_type=float,
        description="Overall sentiment score (-1 to +1)",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.BETWEEN,
        ],
        default_operator=ComparisonOperator.GREATER_THAN
    ),
    
    "analyst_rating": FilterCriteria(
        name="analyst_rating",
        display_name="Analyst Rating",
        category=CriteriaType.SENTIMENT,
        data_type=str,
        description="Analyst consensus rating",
        valid_operators=[
            ComparisonOperator.EQUALS,
            ComparisonOperator.IN,
        ],
        default_operator=ComparisonOperator.EQUALS
    ),
    
    # Market Criteria
    "sector": FilterCriteria(
        name="sector",
        display_name="Sector",
        category=CriteriaType.MARKET,
        data_type=str,
        description="Stock sector",
        valid_operators=[
            ComparisonOperator.EQUALS,
            ComparisonOperator.IN,
            ComparisonOperator.NOT_IN,
        ],
        default_operator=ComparisonOperator.EQUALS
    ),
    
    "industry": FilterCriteria(
        name="industry",
        display_name="Industry",
        category=CriteriaType.MARKET,
        data_type=str,
        description="Stock industry",
        valid_operators=[
            ComparisonOperator.EQUALS,
            ComparisonOperator.IN,
            ComparisonOperator.NOT_IN,
        ],
        default_operator=ComparisonOperator.EQUALS
    ),
    
    "exchange": FilterCriteria(
        name="exchange",
        display_name="Exchange",
        category=CriteriaType.MARKET,
        data_type=str,
        description="Stock exchange (NYSE, NASDAQ, etc.)",
        valid_operators=[
            ComparisonOperator.EQUALS,
            ComparisonOperator.IN,
        ],
        default_operator=ComparisonOperator.EQUALS
    ),
    
    # Performance Criteria
    "return_1w": FilterCriteria(
        name="return_1w",
        display_name="1-Week Return",
        category=CriteriaType.PERFORMANCE,
        data_type=float,
        description="1-week percentage return",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.BETWEEN,
        ],
        default_operator=ComparisonOperator.GREATER_THAN,
        unit="%"
    ),
    
    "return_1m": FilterCriteria(
        name="return_1m",
        display_name="1-Month Return",
        category=CriteriaType.PERFORMANCE,
        data_type=float,
        description="1-month percentage return",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.BETWEEN,
        ],
        default_operator=ComparisonOperator.GREATER_THAN,
        unit="%"
    ),
    
    "return_ytd": FilterCriteria(
        name="return_ytd",
        display_name="YTD Return",
        category=CriteriaType.PERFORMANCE,
        data_type=float,
        description="Year-to-date percentage return",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.BETWEEN,
        ],
        default_operator=ComparisonOperator.GREATER_THAN,
        unit="%"
    ),
    
    # Risk Criteria
    "beta": FilterCriteria(
        name="beta",
        display_name="Beta",
        category=CriteriaType.RISK,
        data_type=float,
        description="Stock beta (market correlation)",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.BETWEEN,
        ],
        default_operator=ComparisonOperator.LESS_THAN
    ),
    
    "volatility": FilterCriteria(
        name="volatility",
        display_name="Volatility",
        category=CriteriaType.RISK,
        data_type=float,
        description="30-day volatility percentage",
        valid_operators=[
            ComparisonOperator.GREATER_THAN,
            ComparisonOperator.LESS_THAN,
            ComparisonOperator.BETWEEN,
        ],
        default_operator=ComparisonOperator.LESS_THAN,
        unit="%"
    ),
}


def get_criteria_by_name(name: str) -> Optional[FilterCriteria]:
    """Get filter criteria by name"""
    return AVAILABLE_CRITERIA.get(name)


def get_criteria_by_category(category: CriteriaType) -> List[FilterCriteria]:
    """Get all criteria in a specific category"""
    return [c for c in AVAILABLE_CRITERIA.values() if c.category == category]


def get_all_criteria() -> List[FilterCriteria]:
    """Get all available filter criteria"""
    return list(AVAILABLE_CRITERIA.values())
