"""
Portfolio API router.

Endpoints
---------
GET /portfolio/summary   — total value, cash, P&L, benchmark comparison
GET /portfolio/positions — open positions with current prices
GET /portfolio/history   — closed trades + daily equity snapshots

Requirements: R2.1–R2.8, R7.3
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from dependencies import get_current_user, get_db
from auth.models import User
from portfolio.schemas import (
    PortfolioHistoryResponse,
    PortfolioSummaryResponse,
    PositionDetail,
)
from portfolio.service import PortfolioService

router = APIRouter()


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return the enriched portfolio summary: account totals, P&L metrics,
    win-rate statistics, and a SPY benchmark comparison (R2.1, R2.2, R2.5, R2.7).
    """
    service = PortfolioService(db=db, user_id=current_user.id)
    return service.get_summary()


@router.get("/positions", response_model=list[PositionDetail])
async def get_positions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return all open positions enriched with today's day-change % (R2.3).
    """
    service = PortfolioService(db=db, user_id=current_user.id)
    return service.get_positions()


@router.get("/history", response_model=PortfolioHistoryResponse)
async def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return closed-trade records and daily equity snapshots (R2.4, R2.6).
    """
    service = PortfolioService(db=db, user_id=current_user.id)
    return service.get_history()
