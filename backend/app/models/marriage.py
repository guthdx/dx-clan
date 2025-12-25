import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Marriage(Base):
    __tablename__ = "marriages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    spouse1_id = Column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    spouse2_id = Column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    marriage_order = Column(Integer, default=1)  # 1st, 2nd, 3rd marriage for spouse1
    marriage_year = Column(Integer, nullable=True)
    divorce_year = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    spouse1 = relationship(
        "Person",
        foreign_keys=[spouse1_id],
        back_populates="marriages_as_spouse1"
    )
    spouse2 = relationship(
        "Person",
        foreign_keys=[spouse2_id],
        back_populates="marriages_as_spouse2"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("spouse1_id", "spouse2_id", name="unique_marriage_pair"),
    )
