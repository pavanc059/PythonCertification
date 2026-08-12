"""
Pydantic v2 request / response schemas for the trading module.

Requirements: R4.2, R5.1–R5.8, R7.5, R8.1, R8.2
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal, Optional


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class PlaceOrderRequest(BaseModel):
    """Body expected by POST /trading/orders."""

    ticker: str
    side: str           # "buy" | "sell"
    order_type: str     # "market" | "limit" | "stop_loss" | "stop_limit"
    quantity: int
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None

    @field_validator("ticker")
    @classmethod
    def ticker_upper(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("side")
    @classmethod
    def valid_side(cls, v: str) -> str:
        if v not in ("buy", "sell"):
            raise ValueError("side must be 'buy' or 'sell'")
        return v

    @field_validator("order_type")
    @classmethod
    def valid_order_type(cls, v: str) -> str:
        valid = ("market", "limit", "stop_loss", "stop_limit")
        if v not in valid:
            raise ValueError(f"order_type must be one of {valid}")
        return v

    @field_validator("quantity")
    @classmethod
    def positive_quantity(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("quantity must be > 0")
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class OrderResponse(BaseModel):
    """Returned by POST /trading/orders."""

    status: str
    order_id: Optional[str] = None
    filled_price: Optional[float] = None
    filled_quantity: Optional[int] = None
    commission: Optional[float] = None
    slippage: Optional[float] = None
    reason: Optional[str] = None


class AccountSummaryResponse(BaseModel):
    """Returned by GET /trading/account."""

    account_id: str
    cash: float
    portfolio_value: float
    total_value: float
    buying_power: float
    total_return: float
    total_return_pct: float
    num_positions: int
    num_pending_orders: int
    created_at: str


class PositionResponse(BaseModel):
    """One open position, returned in a list by GET /trading/positions."""

    ticker: str
    quantity: int
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    cost_basis: float


class OrderHistoryItem(BaseModel):
    """One order record, returned in a list by GET /trading/orders."""

    order_id: str
    ticker: str
    side: str
    order_type: str
    quantity: int
    limit_price: Optional[float]
    stop_price: Optional[float]
    status: str
    filled_price: Optional[float]
    filled_quantity: int
    commission: float
    slippage: float
    created_at: str
    filled_at: Optional[str]


class ResetResponse(BaseModel):
    """Returned by POST /trading/reset."""

    message: str
    new_balance: float


class RealOrderRequest(BaseModel):
    """Request body for POST /trading/real/confirm."""

    ticker: str
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit", "stop_loss", "stop_limit"]
    quantity: int = Field(gt=0)
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    confirmation_text: str  # Must equal "{TICKER} {QTY} {SIDE}" (case-insensitive)

    @field_validator("ticker")
    @classmethod
    def ticker_upper(cls, v: str) -> str:
        return v.upper().strip()


class RealOrderConfirmResponse(BaseModel):
    """Returned by POST /trading/real/confirm."""

    order_id: str
    status: str    # "submitted" | "rejected"
    message: str
