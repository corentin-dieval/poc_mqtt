from typing import Literal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event
from app.schemas.status import GlobalStatus, MachineStatus


async def get_consolidated_status(db: AsyncSession) -> GlobalStatus:
    """
    Compute the latest status for each machine.
    global_status is NG if at least one machine is NG.
    Uses a correlated subquery compatible with both PostgreSQL and SQLite (tests).
    """
    # Latest timestamp per machine
    latest_ts_subq = (
        select(Event.machine_id, func.max(Event.timestamp).label("max_ts"))
        .group_by(Event.machine_id)
        .subquery()
    )

    # Join back to get the status at that timestamp
    stmt = (
        select(Event.machine_id, Event.status, Event.timestamp)
        .join(
            latest_ts_subq,
            (Event.machine_id == latest_ts_subq.c.machine_id)
            & (Event.timestamp == latest_ts_subq.c.max_ts),
        )
    )

    result = await db.execute(stmt)
    rows = result.fetchall()

    machines: list[MachineStatus] = [
        MachineStatus(machine_id=row.machine_id, status=row.status, last_seen=row.timestamp)
        for row in rows
    ]

    global_status: Literal["OK", "NG"] = (
        "NG" if any(m.status == "NG" for m in machines) else "OK"
    )

    return GlobalStatus(global_status=global_status, machines=machines)
