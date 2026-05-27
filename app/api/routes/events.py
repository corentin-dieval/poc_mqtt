from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.event import EventListResponse, EventResponse
from app.services import event_service

router = APIRouter(tags=["events"])


@router.get("/events", response_model=EventListResponse)
async def list_events(
    page: int = Query(default=1, ge=1, description="Numéro de page"),
    page_size: int = Query(default=50, ge=1, le=200, description="Nombre d'éléments par page"),
    db: AsyncSession = Depends(get_db),
) -> EventListResponse:
    """Retourne les derniers événements avec pagination."""
    events, total = await event_service.get_events(db, page=page, page_size=page_size)
    return EventListResponse(
        items=[EventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )

