from datetime import datetime, timezone
import uuid
from sqlalchemy import String, Float, DateTime, ForeignKey, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SensorData(Base):
    __tablename__ = "sensor_data"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    floor: Mapped[str] = mapped_column(String(50), nullable=False)
    slot_number: Mapped[str | None] = mapped_column(String(10), nullable=True)
    is_occupied: Mapped[bool] = mapped_column(Boolean, default=False)
    type: Mapped[str | None] = mapped_column(String(30), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    locked: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="sensor_data")

    __table_args__ = (
        Index("idx_device_timestamp", "device_id", "timestamp"),
    )