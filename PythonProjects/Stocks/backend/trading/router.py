"""
Trading router — /trading/* endpoints.

Endpoints
---------
GET    /trading/account              — return account summary
POST   /trading/orders               — place market/limit/stop orders
GET    /trading/orders               — return all orders (pending + completed)
DELETE /trading/orders/{order_id}    — cancel a pending order
GET    /trading/positions            — return all open positions
POST   /trading/reset                — reset account to $100,000
POST   /trading/real/confirm         — real-money order confirmation gate

Requirements: R4.2, R5.1–R5.8, R7.5, R8.1–R8.6
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from dependencies import get_current_user, get_db
from auth.models import User
from trading.schemas import (
    PlaceOrderRequest,
    OrderResponse,
    AccountSummaryResponse,
    PositionResponse,
    OrderHistoryItem,
    ResetResponse,
    RealOrderRequest,
    RealOrderConfirmResponse,
)
from trading.service import TradingService
from trading.confirmation_service import TradingConfirmationService

router = APIRouter()


@router.get("/account", response_model=AccountSummaryResponse)
async def get_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AccountSummaryResponse:
    """Return the authenticated user's paper trading account summary."""
    service = TradingService(db=db, user_id=current_user.id)
    return service.get_account_summary()


@router.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_order(
    body: PlaceOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrderResponse:
    """
    Place a market, limit, stop-loss, or stop-limit order.

    The engine executes market orders immediately; limit/stop orders are
    queued as pending until the trigger price is reached.
    """
    service = TradingService(db=db, user_id=current_user.id)
    result = service.place_order(
        ticker=body.ticker,
        side=body.side,
        order_type=body.order_type,
        quantity=body.quantity,
        limit_price=body.limit_price,
        stop_price=body.stop_price,
    )

    # Convert Decimal values from the engine result to float for serialisation
    for field in ("filled_price", "commission", "slippage"):
        if field in result and result[field] is not None:
            result[field] = float(result[field])

    return result


@router.get("/orders", response_model=list[OrderHistoryItem])
async def get_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[OrderHistoryItem]:
    """Return all orders (pending + completed) for the authenticated user."""
    service = TradingService(db=db, user_id=current_user.id)
    return service.get_orders()


@router.get("/positions", response_model=list[PositionResponse])
async def get_positions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[PositionResponse]:
    """Return all open positions for the authenticated user."""
    service = TradingService(db=db, user_id=current_user.id)
    return service.get_positions()


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Cancel a pending order by its order_id.

    Returns 404 if the order is not found or is already filled/cancelled.
    """
    service = TradingService(db=db, user_id=current_user.id)
    success = service.cancel_order(order_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found or cannot be cancelled.",
        )
    return {"message": f"Order {order_id} cancelled"}


@router.post("/reset", response_model=ResetResponse)
async def reset_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ResetResponse:
    """
    Reset the paper trading account back to its initial $100,000 balance.

    All open positions and pending orders are cleared (R4.2).
    """
    service = TradingService(db=db, user_id=current_user.id)
    service.reset_account()
    return {"message": "Account reset to $100,000", "new_balance": 100_000.0}


@router.post("/real/confirm", response_model=RealOrderConfirmResponse, status_code=201)
async def confirm_real_order(
    body: RealOrderRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RealOrderConfirmResponse:
    """
    Gate for real-money order submission.

    Validates the user's typed confirmation string, writes an immutable
    audit log entry, and (on success) forwards to the real broker adapter.

    Returns 403 if the user does not have real-money trading enabled.
    Returns 422 if the confirmation text does not match exactly.
    Returns 201 with order_id and status on success.

    NOTE: This endpoint will NEVER call Webull's order placement API.
    The broker adapter is a stub in v1; wiring to a real broker is a
    separate, explicitly-scoped future task.

    Requirements: R8.1, R8.2, R8.3, R8.4, R8.5, R8.6
    """
    # Paper-mode guard: check for real-money flag on the user account.
    # Using getattr with a False default so this works even if the User model
    # does not yet have the is_real_money_enabled column. All users are treated
    # as paper-mode by default — real-money must be explicitly enabled.
    # TODO: Add is_real_money_enabled to the User model when real-money
    # account flags are implemented.
    if not getattr(current_user, "is_real_money_enabled", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Real-money trading is not enabled for this account.",
        )

    # get_redis_client is not available in dependencies; set to None.
    # TradingConfirmationService degrades gracefully without Redis.
    redis = None

    service = TradingConfirmationService(
        db=db, redis_client=redis, user_id=current_user.id
    )
    result = service.validate_and_submit(
        order=body,
        confirmation_text=body.confirmation_text,
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=result.reason,
        )

    return RealOrderConfirmResponse(
        order_id=result.order_id,
        status="submitted",
        message="Real order confirmed and submitted for processing.",
    )
