from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base, Event
from app.schemas.event import EventPayload
from app.schemas.status import GlobalStatus
from app.services.event_service import DuplicateEventError, save_event
from app.services.status_service import get_consolidated_status

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine(TEST_DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


def make_payload(machine_id: str, status: str, event_id: str | None = None) -> EventPayload:
    import uuid
    return EventPayload(
        event_id=uuid.UUID(event_id) if event_id else uuid.uuid4(),
        machine_id=machine_id,
        timestamp=datetime.now(UTC),
        status=status,
    )


@pytest.mark.asyncio
async def test_save_event(db: AsyncSession):
    payload = make_payload("MACHINE_01", "OK")
    event = await save_event(db, payload)
    assert isinstance(event, Event)
    assert event.machine_id == "MACHINE_01"
    assert event.status == "OK"


@pytest.mark.asyncio
async def test_save_duplicate_event(db: AsyncSession):
    payload = make_payload("MACHINE_01", "OK", "550e8400-e29b-41d4-a716-446655440000")
    await save_event(db, payload)
    with pytest.raises(DuplicateEventError):
        await save_event(db, payload)


@pytest.mark.asyncio
async def test_consolidated_status_all_ok(db: AsyncSession):
    await save_event(db, make_payload("MACHINE_01", "OK"))
    await save_event(db, make_payload("MACHINE_02", "OK"))
    result: GlobalStatus = await get_consolidated_status(db)
    assert result.global_status == "OK"
    assert len(result.machines) == 2


@pytest.mark.asyncio
async def test_consolidated_status_any_ng(db: AsyncSession):
    await save_event(db, make_payload("MACHINE_01", "OK"))
    await save_event(db, make_payload("MACHINE_02", "NG"))
    result: GlobalStatus = await get_consolidated_status(db)
    assert result.global_status == "NG"


@pytest.mark.asyncio
async def test_consolidated_status_empty(db: AsyncSession):
    result: GlobalStatus = await get_consolidated_status(db)
    assert result.global_status == "OK"
    assert result.machines == []

