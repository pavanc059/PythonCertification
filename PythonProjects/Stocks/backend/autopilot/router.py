"""
AutoPilot API router.

Endpoints (all require JWT auth; market_type path param is "penny" | "regular")

GET   /autopilot/providers                    — list data providers + active one
GET   /autopilot/{market_type}/config         — get (or lazily create) config
PUT   /autopilot/{market_type}/config         — update config
POST  /autopilot/{market_type}/enable         — enable/disable master switch
POST  /autopilot/{market_type}/flatten        — force-close all open positions now
GET   /autopilot/{market_type}/status         — live progress vs target
GET   /autopilot/{market_type}/trades         — trade history (open + closed)
GET   /autopilot/{market_type}/reports        — daily report history

Live auto-trading is PAPER ONLY.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from auth.models import User
from dependencies import get_current_user, get_db
from config import settings

from autopilot.service import AutoPilotService, VALID_MARKET_TYPES
from autopilot.providers import list_providers
from autopilot.schemas import (
    AutoPilotConfigUpdate, AutoPilotConfigResponse, AutoPilotStatusResponse,
    AutoPilotTradeResponse, AutoPilotReportResponse, ProvidersResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _validate_market(market_type: str) -> str:
    if market_type not in VALID_MARKET_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"market_type must be one of {VALID_MARKET_TYPES}",
        )
    return market_type


@router.get("/providers", response_model=ProvidersResponse)
async def get_providers(current_user: User = Depends(get_current_user)):
    """List available market-data providers and the active default."""
    return {"providers": list_providers(), "active": settings.autopilot_data_provider}


@router.get("/{market_type}/config", response_model=AutoPilotConfigResponse)
async def get_config(
    market_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_market(market_type)
    service = AutoPilotService(db, current_user.id)
    config = service.get_or_create_config(market_type)
    return service.config_to_dict(config)


@router.put("/{market_type}/config", response_model=AutoPilotConfigResponse)
async def update_config(
    market_type: str,
    body: AutoPilotConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_market(market_type)
    service = AutoPilotService(db, current_user.id)
    config = service.update_config(market_type, body.model_dump(exclude_unset=True))
    return service.config_to_dict(config)


@router.post("/{market_type}/enable", response_model=AutoPilotConfigResponse)
async def set_enabled(
    market_type: str,
    enabled: bool = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Toggle the master switch. Disabling force-flattens open positions so the
    account is never left with orphaned AutoPilot positions.
    """
    _validate_market(market_type)
    service = AutoPilotService(db, current_user.id)
    config = service.get_or_create_config(market_type)

    if not enabled and config.enabled:
        # Flatten before disabling
        from autopilot.executor import AutoPilotExecutor
        AutoPilotExecutor(db).force_flat(config.id, reason="disabled")

    config = service.update_config(market_type, {"enabled": enabled})
    return service.config_to_dict(config)


@router.post("/{market_type}/flatten", response_model=AutoPilotStatusResponse)
async def flatten(
    market_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Immediately close all open AutoPilot positions for this market type."""
    _validate_market(market_type)
    service = AutoPilotService(db, current_user.id)
    config = service.get_or_create_config(market_type)

    from autopilot.executor import AutoPilotExecutor
    AutoPilotExecutor(db).force_flat(config.id, reason="manual")
    return service.status_dict(market_type)


@router.get("/{market_type}/status", response_model=AutoPilotStatusResponse)
async def get_status(
    market_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_market(market_type)
    service = AutoPilotService(db, current_user.id)
    return service.status_dict(market_type)


@router.get("/{market_type}/trades", response_model=list[AutoPilotTradeResponse])
async def get_trades(
    market_type: str,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_market(market_type)
    service = AutoPilotService(db, current_user.id)
    return [service.trade_to_dict(t) for t in service.get_trades(market_type, limit)]


@router.get("/{market_type}/reports", response_model=list[AutoPilotReportResponse])
async def get_reports(
    market_type: str,
    limit: int = 60,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_market(market_type)
    service = AutoPilotService(db, current_user.id)
    return [service.report_to_dict(r) for r in service.get_reports(market_type, limit)]
