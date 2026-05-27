import asyncio
import json
import threading
import time

import paho.mqtt.client as mqtt
from pydantic import ValidationError

from app.core.config import Settings
from app.core.logging import get_logger
from app.db.database import AsyncSessionLocal
from app.schemas.event import EventPayload
from app.services.event_service import DuplicateEventError, save_event

logger = get_logger(__name__)


class MQTTClient:
    """
    Async-compatible MQTT client.
    Runs paho's network loop in a background thread and dispatches
    message processing to the asyncio event loop.
    """

    def __init__(self, settings: Settings, loop: asyncio.AbstractEventLoop) -> None:
        self._settings = settings
        self._loop = loop
        self._client = mqtt.Client(
            client_id=settings.MQTT_CLIENT_ID,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        self._thread: threading.Thread | None = None
        self._running = False

    # ------------------------------------------------------------------
    # Callbacks (called from paho's background thread)
    # ------------------------------------------------------------------

    def _on_connect(self, client: mqtt.Client, userdata, flags, reason_code, properties) -> None:  # noqa: ANN001
        if reason_code == 0:
            logger.info(
                "MQTT connected to %s:%s — subscribing to '%s'",
                self._settings.MQTT_BROKER_HOST,  # Correction de la faute de frappe ici
                self._settings.MQTT_BROKER_PORT,
                self._settings.MQTT_TOPIC_PATTERN,
            )
            client.subscribe(self._settings.MQTT_TOPIC_PATTERN)
        else:
            logger.error("MQTT connection refused: reason_code=%s", reason_code)

    def _on_disconnect(self, client: mqtt.Client, userdata, disconnect_flags, reason_code, properties) -> None:  # noqa: ANN001
        if self._running:
            logger.warning("MQTT disconnected (reason=%s), will reconnect…", reason_code)

    def _on_message(self, client: mqtt.Client, userdata, message: mqtt.MQTTMessage) -> None:  # noqa: ANN001
        topic = message.topic
        try:
            raw = json.loads(message.payload.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.warning("MQTT invalid JSON on topic %s: %s", topic, exc)
            return

        try:
            payload = EventPayload.model_validate(raw)
        except ValidationError as exc:
            logger.warning("MQTT payload validation failed on topic %s: %s", topic, exc)
            return

        # Schedule coroutine on the asyncio loop from this background thread
        asyncio.run_coroutine_threadsafe(self._persist_event(payload), self._loop)

    # ------------------------------------------------------------------
    # Async persistence
    # ------------------------------------------------------------------

    async def _persist_event(self, payload: EventPayload) -> None:
        async with AsyncSessionLocal() as db:
            try:
                await save_event(db, payload)
            except DuplicateEventError:
                pass  # Already logged in service layer
            except Exception as exc:
                logger.error("Failed to persist event %s: %s", payload.event_id, exc)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _connect_with_retry(self) -> None:
        while self._running:
            try:
                self._client.connect(
                    self._settings.MQTT_BROKER_HOST,
                    self._settings.MQTT_BROKER_PORT,
                    keepalive=60,
                )
                self._client.loop_forever(retry_first_connection=True)
                break
            except OSError as exc:
                logger.warning(
                    "MQTT connection error: %s — retrying in %ds",
                    exc,
                    self._settings.MQTT_RECONNECT_DELAY,
                )
                time.sleep(self._settings.MQTT_RECONNECT_DELAY)

    def start(self) -> None:
        """Start the MQTT client in a background daemon thread."""
        self._running = True
        self._thread = threading.Thread(target=self._connect_with_retry, daemon=True, name="mqtt-client")
        self._thread.start()
        logger.info("MQTT client thread started")

    def stop(self) -> None:
        """Gracefully disconnect the MQTT client."""
        self._running = False
        self._client.disconnect()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("MQTT client stopped")
