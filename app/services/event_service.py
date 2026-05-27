from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Event
from app.schemas.event import EventPayload

logger = get_logger(__name__)


class DuplicateEventError(Exception):
    """Raised when an event_id already exists in the database."""


async def save_event(db: AsyncSession, payload: EventPayload) -> Event:
    """
    Persist a validated MQTT event payload.
    Raises DuplicateEventError if event_id already exists.
    """
    event = Event(
        event_id=str(payload.event_id),
        id_product=payload.id_product,  # Nouveau champ
        ipc_source_hostname=payload.ipc_source_hostname,  # Nouveau champ
        plm_workcenter=payload.plm_workcenter,  # Nouveau champ
        plm_workunit=payload.plm_workunit,  # Nouveau champ
        machine_id=payload.machine_id,
        timestamp=payload.timestamp,
        status=payload.status,
        raw_payload=payload.model_dump(mode="json"),
    )
    db.add(event)
    try:
        await db.commit()
        await db.refresh(event)
        logger.info(
            "Event saved: %s id_product=%s machine=%s workcenter=%s status=%s",
            event.event_id,
            event.id_product,
            event.machine_id,
            event.plm_workcenter,
            event.status,
        )
        return event
    except IntegrityError:
        await db.rollback()
        logger.warning("Duplicate event_id ignored: %s", payload.event_id)
        raise DuplicateEventError(f"event_id {payload.event_id} already exists")


async def get_events(
    db: AsyncSession, page: int = 1, page_size: int = 50
) -> tuple[list[Event], int]:
    """Return paginated events ordered by timestamp descending."""
    offset = (page - 1) * page_size

    total_result = await db.execute(select(func.count()).select_from(Event))
    total = total_result.scalar_one()

    result = await db.execute(
        select(Event).order_by(Event.timestamp.desc()).offset(offset).limit(page_size)
    )
    events = list(result.scalars().all())

    return events, total
