from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.models import Base, Event
from app.schemas.event import EventPayload
from app.schemas.status import GlobalStatus, ProductStatus, MachineStatus
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


def make_payload(
    machine_id: str,
    status: str,
    event_id: str | None = None,
    id_product: str = "PRODUCT_A",
    ipc_source_hostname: str = "host-1",
    plm_workcenter: str = "WC_1",
    plm_workunit: str = "WU_1",
    timestamp: datetime | None = None,
) -> EventPayload:
    import uuid
    return EventPayload(
        event_id=uuid.UUID(event_id) if event_id else uuid.uuid4(),
        id_product=id_product,
        ipc_source_hostname=ipc_source_hostname,
        plm_workcenter=plm_workcenter,
        plm_workunit=plm_workunit,
        machine_id=machine_id,
        timestamp=timestamp if timestamp else datetime.now(UTC),
        status=status,
    )


@pytest.mark.asyncio
async def test_save_event(db: AsyncSession):
    payload = make_payload("MACHINE_01", "OK")
    event = await save_event(db, payload)
    assert isinstance(event, Event)
    assert event.event_id == str(payload.event_id)
    assert event.id_product == payload.id_product
    assert event.ipc_source_hostname == payload.ipc_source_hostname
    assert event.plm_workcenter == payload.plm_workcenter
    assert event.plm_workunit == payload.plm_workunit
    assert event.machine_id == "MACHINE_01"
    assert event.status == "OK"


@pytest.mark.asyncio
async def test_save_duplicate_event(db: AsyncSession):
    payload = make_payload("MACHINE_01", "OK", "550e8400-e29b-41d4-a716-446655440000")
    await save_event(db, payload)
    with pytest.raises(DuplicateEventError):
        await save_event(db, payload)


@pytest.mark.asyncio
async def test_consolidated_status_single_product_all_ok(db: AsyncSession):
    # Two machines for PRODUCT_A, both OK
    await save_event(db, make_payload("MACHINE_01", "OK", id_product="PRODUCT_A", timestamp=datetime(2023, 1, 1, 10, 0, 0, tzinfo=UTC)))
    await save_event(db, make_payload("MACHINE_02", "OK", id_product="PRODUCT_A", timestamp=datetime(2023, 1, 1, 10, 1, 0, tzinfo=UTC)))
    
    result: GlobalStatus = await get_consolidated_status(db)
    assert result.global_summary_status == "OK"
    assert len(result.items) == 1
    
    product_a_status = result.items[0]
    assert product_a_status.id_product == "PRODUCT_A"
    assert product_a_status.status == "OK"
    assert product_a_status.last_seen == datetime(2023, 1, 1, 10, 1, 0, tzinfo=UTC)
    assert len(product_a_status.machines) == 2
    assert any(m.machine_id == "MACHINE_01" and m.status == "OK" for m in product_a_status.machines)
    assert any(m.machine_id == "MACHINE_02" and m.status == "OK" for m in product_a_status.machines)


@pytest.mark.asyncio
async def test_consolidated_status_single_product_any_ng(db: AsyncSession):
    # Two machines for PRODUCT_A, one NG
    await save_event(db, make_payload("MACHINE_01", "OK", id_product="PRODUCT_A", timestamp=datetime(2023, 1, 1, 10, 0, 0, tzinfo=UTC)))
    await save_event(db, make_payload("MACHINE_02", "NG", id_product="PRODUCT_A", timestamp=datetime(2023, 1, 1, 10, 1, 0, tzinfo=UTC)))
    
    result: GlobalStatus = await get_consolidated_status(db)
    assert result.global_summary_status == "NG"
    assert len(result.items) == 1
    
    product_a_status = result.items[0]
    assert product_a_status.id_product == "PRODUCT_A"
    assert product_a_status.status == "NG"
    assert product_a_status.last_seen == datetime(2023, 1, 1, 10, 1, 0, tzinfo=UTC)
    assert len(product_a_status.machines) == 2
    assert any(m.machine_id == "MACHINE_01" and m.status == "OK" for m in product_a_status.machines)
    assert any(m.machine_id == "MACHINE_02" and m.status == "NG" for m in product_a_status.machines)


@pytest.mark.asyncio
async def test_consolidated_status_multiple_products(db: AsyncSession):
    # PRODUCT_A: MACHINE_01 (OK), MACHINE_02 (NG) -> PRODUCT_A is NG
    await save_event(db, make_payload("MACHINE_01", "OK", id_product="PRODUCT_A", timestamp=datetime(2023, 1, 1, 10, 0, 0, tzinfo=UTC)))
    await save_event(db, make_payload("MACHINE_02", "NG", id_product="PRODUCT_A", timestamp=datetime(2023, 1, 1, 10, 1, 0, tzinfo=UTC)))
    
    # PRODUCT_B: MACHINE_03 (OK), MACHINE_04 (OK) -> PRODUCT_B is OK
    await save_event(db, make_payload("MACHINE_03", "OK", id_product="PRODUCT_B", timestamp=datetime(2023, 1, 1, 10, 2, 0, tzinfo=UTC)))
    await save_event(db, make_payload("MACHINE_04", "OK", id_product="PRODUCT_B", timestamp=datetime(2023, 1, 1, 10, 3, 0, tzinfo=UTC)))

    result: GlobalStatus = await get_consolidated_status(db)
    assert result.global_summary_status == "NG" # Because PRODUCT_A is NG
    assert len(result.items) == 2

    product_a_status = next(p for p in result.items if p.id_product == "PRODUCT_A")
    assert product_a_status.status == "NG"
    assert len(product_a_status.machines) == 2

    product_b_status = next(p for p in result.items if p.id_product == "PRODUCT_B")
    assert product_b_status.status == "OK"
    assert len(product_b_status.machines) == 2


@pytest.mark.asyncio
async def test_consolidated_status_empty(db: AsyncSession):
    result: GlobalStatus = await get_consolidated_status(db)
    assert result.global_summary_status == "OK"
    assert result.items == []

