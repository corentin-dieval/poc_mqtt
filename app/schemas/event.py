from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class EventPayload(BaseModel):
    """Payload reçu via MQTT — format standardisé."""

    event_id: UUID
    machine_id: str
    timestamp: datetime
    status: Literal["OK", "NG"]

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (ISO8601 UTC)")
        return v

    @field_validator("machine_id")
    @classmethod
    def machine_id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("machine_id must not be empty")
        return v.strip()


class EventResponse(BaseModel):
    """Réponse API pour un événement."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    machine_id: str
    timestamp: datetime
    status: str
    created_at: datetime


class EventListResponse(BaseModel):
    """Réponse paginée pour la liste des événements."""

    items: list[EventResponse]
    total: int
    page: int
    page_size: int

