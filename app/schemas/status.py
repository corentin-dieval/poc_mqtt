from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class MachineStatus(BaseModel):
    machine_id: str
    status: Literal["OK", "NG"]
    last_seen: datetime


class GlobalStatus(BaseModel):
    global_status: Literal["OK", "NG"]
    machines: list[MachineStatus]

