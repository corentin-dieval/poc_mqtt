from datetime import datetime, timezone
from typing import List, Literal, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Event
from app.schemas.status import MachineStatus, ProductStatus


async def get_consolidated_status(db: AsyncSession, id_product: str) -> Optional[ProductStatus]:
    """
    Compute the latest status for each machine associated with a specific id_product.
    A product's status is NG if at least one of its machines is NG.
    Returns a single ProductStatus object for the given id_product, or None if not found.
    """
    # Subquery to find the latest timestamp for each machine_id, filtered by the requested id_product
    latest_machine_ts_subq = (
        select(
            Event.machine_id,
            func.max(Event.timestamp).label("max_ts")
        )
        .filter(Event.id_product == id_product) # Filter here for efficiency
        .group_by(Event.machine_id)
        .subquery()
    )

    # Select the full event details for these latest timestamps
    latest_events_per_machine_stmt = (
        select(
            Event.id_product,
            Event.machine_id,
            Event.status,
            Event.timestamp
        )
        .join(
            latest_machine_ts_subq,
            (Event.machine_id == latest_machine_ts_subq.c.machine_id)
            & (Event.timestamp == latest_machine_ts_subq.c.max_ts)
        )
    )
    
    result = await db.execute(latest_events_per_machine_stmt)
    latest_machine_events = result.fetchall()

    if not latest_machine_events:
        return None # No events found for this id_product

    # Initialize product data for the single requested id_product
    product_data = {
        "machines": [],
        "product_status": "OK", # Assume OK initially
        "last_seen": datetime.min.replace(tzinfo=timezone.utc) # Initialize with a very old date
    }

    for row in latest_machine_events:
        machine_status = MachineStatus(
            machine_id=row.machine_id,
            status=row.status,
            last_seen=row.timestamp
        )

        product_data["machines"].append(machine_status)

        # Update product_status: if any machine is NG, product is NG
        if machine_status.status == "NG":
            product_data["product_status"] = "NG"

        # Update last_seen for the product
        if machine_status.last_seen > product_data["last_seen"]:
            product_data["last_seen"] = machine_status.last_seen

    # Construct and return the single ProductStatus object
    return ProductStatus(
        id_product=id_product,
        status=product_data["product_status"],
        last_seen=product_data["last_seen"],
        machines=sorted(product_data["machines"], key=lambda m: m.machine_id) # Sort machines for consistent output
    )
