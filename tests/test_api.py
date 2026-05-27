import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import get_db
from app.db.models import Base
from app.main import app
from tests.test_services import make_payload, save_event # Import make_payload and save_event from test_services

# In-memory SQLite for tests (aiosqlite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_events_empty(client: AsyncClient):
    response = await client.get("/events")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] == 0
    assert data["page"] == 1


@pytest.mark.asyncio
async def test_events_pagination_params(client: AsyncClient):
    response = await client.get("/events?page=2&page_size=10")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_status_empty(client: AsyncClient, db_session: AsyncSession):
    response = await client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert "global_summary_status" in data
    assert "items" in data
    assert data["global_summary_status"] == "OK"
    assert data["items"] == []


@pytest.mark.asyncio
async def test_status_consolidated_logic(client: AsyncClient, db_session: AsyncSession):
    # Product A: Machine 1 (OK), Machine 2 (NG) -> Product A is NG
    await save_event(db_session, make_payload("MACHINE_01", "OK", id_product="PRODUCT_A"))
    await save_event(db_session, make_payload("MACHINE_02", "NG", id_product="PRODUCT_A"))

    # Product B: Machine 3 (OK), Machine 4 (OK) -> Product B is OK
    await save_event(db_session, make_payload("MACHINE_03", "OK", id_product="PRODUCT_B"))
    await save_event(db_session, make_payload("MACHINE_04", "OK", id_product="PRODUCT_B"))

    response = await client.get("/status")
    assert response.status_code == 200
    data = response.json()

    assert data["global_summary_status"] == "NG" # Because PRODUCT_A is NG
    assert len(data["items"]) == 2

    product_a_status = next(item for item in data["items"] if item["id_product"] == "PRODUCT_A")
    assert product_a_status["status"] == "NG"
    assert len(product_a_status["machines"]) == 2
    assert any(m["machine_id"] == "MACHINE_01" and m["status"] == "OK" for m in product_a_status["machines"])
    assert any(m["machine_id"] == "MACHINE_02" and m["status"] == "NG" for m in product_a_status["machines"])

    product_b_status = next(item for item in data["items"] if item["id_product"] == "PRODUCT_B")
    assert product_b_status["status"] == "OK"
    assert len(product_b_status["machines"]) == 2
    assert any(m["machine_id"] == "MACHINE_03" and m["status"] == "OK" for m in product_b_status["machines"])
    assert any(m["machine_id"] == "MACHINE_04" and m["status"] == "OK" for m in product_b_status["machines"])

