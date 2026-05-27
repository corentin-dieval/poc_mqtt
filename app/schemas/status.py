from datetime import datetime
from typing import Literal, List

from pydantic import BaseModel


class MachineStatus(BaseModel):
    machine_id: str
    status: Literal["OK", "NG"]
    last_seen: datetime


class ProductStatus(BaseModel):
    """Statut consolidé pour un id_product."""

    id_product: str
    status: Literal["OK", "NG"]
    last_seen: datetime
    machines: List[MachineStatus]


class GlobalStatus(BaseModel):
    """Liste des statuts consolidés par id_product."""

    items: List[ProductStatus]
    global_summary_status: Literal["OK", "NG"]