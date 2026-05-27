import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.api import router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.database import init_db
from app.mqtt.client import MQTTClient

logger = get_logger(__name__)

_mqtt_client: MQTTClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _mqtt_client

    setup_logging()
    logger.info("Starting %s v%s", settings.API_TITLE, settings.API_VERSION)

    await init_db()

    loop = asyncio.get_event_loop()
    _mqtt_client = MQTTClient(settings=settings, loop=loop)
    _mqtt_client.start()

    yield

    logger.info("Shutting down…")
    if _mqtt_client:
        _mqtt_client.stop()


app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="PoC industriel de collecte et consolidation d'événements machines via MQTT.",
    lifespan=lifespan,
)

app.include_router(router)

