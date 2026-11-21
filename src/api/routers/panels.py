"""
Panel washes of the signed-in user's site: the clean events the live dust model measures from.

A wash is always recorded for today (Asia/Karachi), so a user can't rewrite their dust history; recording
it twice on the same day is a no-op. Every query is scoped to the caller's own site.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.api.db.session import get_db
from src.api.deps import get_now
from src.api.site_soiling import RECENT_WASHES, load_washes, record_wash
from src.api.user_site import MySite

router = APIRouter(prefix="/api/panels", tags=["Panels"])

DbSession = Annotated[Session, Depends(get_db)]
Now = Annotated[datetime, Depends(get_now)]


class PanelWashOut(BaseModel):
    # Local day (YYYY-MM-DD, Asia/Karachi).
    washed_on: str


@router.post("/washes", status_code=status.HTTP_201_CREATED, response_model=PanelWashOut)
def record_panel_wash(site: MySite, session: DbSession, now: Now) -> PanelWashOut:
    """Records that the panels were washed today. Idempotent per day."""
    return PanelWashOut(washed_on=record_wash(session, site.site_id, now).isoformat())


@router.get("/washes", response_model=list[PanelWashOut])
def list_panel_washes(
    request: Request, site: MySite, limit: Annotated[int, Query(ge=1, le=RECENT_WASHES)] = RECENT_WASHES
) -> list[PanelWashOut]:
    """The site's latest recorded washes, newest first."""
    washes = load_washes(request.app.state.read_session_factory, site.site_id, limit)
    return [PanelWashOut(washed_on=day.isoformat()) for day in washes]
