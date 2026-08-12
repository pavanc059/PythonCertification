"""
Watchlist API router.

Endpoints
---------
GET    /watchlist              — list all items (optional ?list_name= filter)
POST   /watchlist/add          — add ticker with optional alert price
DELETE /watchlist/{ticker}     — remove ticker from a list
GET    /watchlist/lists        — get all named lists with item counts
POST   /watchlist/lists        — create a new named list

Requirements: R3.1, R3.3, R3.4, R3.7, R7.4
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth.models import User
from dependencies import get_current_user, get_db
from watchlist.schemas import (
    AddWatchlistItemRequest,
    WatchlistItemResponse,
    WatchlistListCreate,
    WatchlistListResponse,
)
from watchlist.service import WatchlistService

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /watchlist
# ---------------------------------------------------------------------------


@router.get("", response_model=list[WatchlistItemResponse])
async def get_watchlist(
    list_name: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return all watchlist items for the current user.

    Optionally filter by ``list_name`` query parameter (R3.4).
    """
    service = WatchlistService(db=db, user_id=current_user.id)
    return service.get_items(list_name=list_name)


# ---------------------------------------------------------------------------
# POST /watchlist/add
# ---------------------------------------------------------------------------


@router.post("/add", response_model=WatchlistItemResponse, status_code=201)
async def add_to_watchlist(
    body: AddWatchlistItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a ticker to the user's watchlist (R3.1).

    Returns 409 if the ticker is already in the specified list.
    """
    service = WatchlistService(db=db, user_id=current_user.id)
    return service.add_item(
        ticker=body.ticker,
        list_name=body.list_name,
        alert_price=body.alert_price,
    )


# ---------------------------------------------------------------------------
# DELETE /watchlist/{ticker}
# ---------------------------------------------------------------------------


@router.delete("/{ticker}", status_code=200)
async def remove_from_watchlist(
    ticker: str,
    list_name: str = "Default",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a ticker from the user's watchlist (R3.3).

    ``list_name`` query parameter selects which list to remove from
    (defaults to "Default").

    Returns 404 when the ticker is not found in the specified list.
    """
    service = WatchlistService(db=db, user_id=current_user.id)
    found = service.remove_item(ticker=ticker.upper(), list_name=list_name)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{ticker.upper()} not found in list '{list_name}'",
        )
    return {"message": f"{ticker.upper()} removed from '{list_name}'"}


# ---------------------------------------------------------------------------
# GET /watchlist/lists
# ---------------------------------------------------------------------------


@router.get("/lists", response_model=list[WatchlistListResponse])
async def get_lists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return distinct named lists for the current user with item counts (R3.4).
    """
    service = WatchlistService(db=db, user_id=current_user.id)
    return service.get_lists()


# ---------------------------------------------------------------------------
# POST /watchlist/lists
# ---------------------------------------------------------------------------


@router.post("/lists", response_model=WatchlistListResponse, status_code=201)
async def create_list(
    body: WatchlistListCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create (or acknowledge) a named watchlist (R3.4).

    If the list already has items the existing metadata is returned;
    otherwise a new empty list is registered.

    Returns 400 when the list name is invalid (enforced by Pydantic schema).
    """
    service = WatchlistService(db=db, user_id=current_user.id)
    return service.create_list(name=body.name)
