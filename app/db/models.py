from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, JSON, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    id_product: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Nouvelle colonne
    ipc_source_hostname: Mapped[str] = mapped_column(String(100), nullable=False)  # Nouvelle colonne
    plm_workcenter: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # Nouvelle colonne
    plm_workunit: Mapped[str] = mapped_column(String(100), nullable=False)  # Nouvelle colonne
    machine_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    raw_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_events_machine_ts", "machine_id", "timestamp"),
        Index("idx_events_id_product", "id_product"),
        Index("idx_events_plm_workcenter", "plm_workcenter"),
    )

    def __repr__(self) -> str:
        return (
            f"<Event {self.event_id} id_product={self.id_product} machine={self.machine_id} "
            f"workcenter={self.plm_workcenter} status={self.status}>"
        )
