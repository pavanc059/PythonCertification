"""
TradingConfirmationService — validates user-typed confirmation strings for
real-money orders and writes an immutable audit log for every attempt.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.6

Security note: This service NEVER accesses WEBULL_TRADING_PIN or any
trading PIN value. It is intentionally excluded from all code paths here.
"""

from dataclasses import dataclass
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from trading.models import RealTradeAuditLog
from trading.schemas import RealOrderRequest


@dataclass
class ConfirmationResult:
    """Result returned by validate_and_submit."""

    success: bool
    order_id: Optional[str] = None
    reason: Optional[str] = None


class TradingConfirmationService:
    """
    Validates typed confirmation strings for real-money orders and records
    every attempt — success or failure — in the real_trade_audit_log table.

    Confirmation challenge format: "{TICKER} {QUANTITY} {SIDE}"
    Example: "AAPL 100 BUY"

    The audit log write is unconditional; it happens regardless of whether
    the confirmation text matches the expected string (Requirement 6.5).
    """

    def __init__(self, db: Session, redis_client, user_id: UUID) -> None:
        self.db = db
        self.redis_client = redis_client
        self.user_id = user_id

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_confirmation_challenge(self, order: RealOrderRequest) -> str:
        """
        Return the exact string the user must type to confirm the order.

        Format: "{TICKER} {QUANTITY} {SIDE}"  e.g. "AAPL 100 BUY"

        Requirements: 6.1
        """
        return f"{order.ticker} {order.quantity} {order.side.upper()}"

    def validate_and_submit(
        self,
        order: RealOrderRequest,
        confirmation_text: str,
        user_id: UUID,
        ip_address: Optional[str] = None,
    ) -> ConfirmationResult:
        """
        Validate the user-typed confirmation string against the expected
        challenge and write an audit log row regardless of outcome.

        Steps:
          1. Build expected = "{ticker} {quantity} {side.upper()}"
          2. Normalise both with .strip().upper()
          3. Compare
          4. ALWAYS write audit log regardless of outcome  (Requirement 6.5)
          5. Return ConfirmationResult

        Requirements: 6.2, 6.3, 6.4, 6.5
        """
        expected = f"{order.ticker} {order.quantity} {order.side.upper()}"
        normalized_input = confirmation_text.strip().upper()
        normalized_expected = expected.strip().upper()

        if normalized_input == normalized_expected:
            outcome = "confirmed"
            result = ConfirmationResult(success=True, order_id=str(uuid4()))
        else:
            outcome = "rejected"
            result = ConfirmationResult(
                success=False,
                reason=f"Confirmation text did not match. Expected: {expected}",
            )

        # ALWAYS write audit log — Requirement 6.5, 7.1
        self._write_audit_log(
            user_id=user_id,
            order=order,
            confirmation_text=confirmation_text,
            outcome=outcome,
            ip_address=ip_address,
        )

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_audit_log(
        self,
        user_id: UUID,
        order: RealOrderRequest,
        confirmation_text: str,
        outcome: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """
        INSERT one row into real_trade_audit_log.

        The row is insert-only; this method never updates or deletes existing
        rows, preserving the immutability guarantee (Requirement 7.3, 7.4).

        Requirements: 7.1, 7.2, 7.6
        """
        row = RealTradeAuditLog(
            user_id=user_id,
            ticker=order.ticker,
            side=order.side,
            order_type=order.order_type,
            quantity=order.quantity,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            confirmation_text=confirmation_text,
            outcome=outcome,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(row)
        self.db.commit()
