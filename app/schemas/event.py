from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class EventPayload(BaseModel):
    """Payload reçu via MQTT — format standardisé."""

    event_id: UUID
    id_product: str
    ipc_source_hostname: str
    plm_workcenter: str
    plm_workunit: str
    machine_id: str
    timestamp: datetime
    status: Literal["OK", "NG"]

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_tz_aware(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (ISO8601 UTC)")
        return v

    @field_validator("machine_id", "id_product", "ipc_source_hostname", "plm_workcenter", "plm_workunit")
    @classmethod
    def string_fields_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("String fields must not be empty")
        return v.strip()


class EventResponse(BaseModel):
    """Réponse API pour un événement."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    id_product: str  # Nouvelle variable
    ipc_source_hostname: str  # Nouvelle variable
    plm_workcenter: str  # Nouvelle variable
    plm_workunit: str  # Nouvelle variable
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

