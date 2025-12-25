import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class ParentChild(Base):
    __tablename__ = "parent_child"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    child_id = Column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    relationship_type = Column(String(50), default="biological")  # 'biological', 'adopted', 'step'
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    parent = relationship(
        "Person",
        foreign_keys=[parent_id],
        back_populates="children_as_parent"
    )
    child = relationship(
        "Person",
        foreign_keys=[child_id],
        back_populates="parents_as_child"
    )

    # Constraints
    __table_args__ = (
        UniqueConstraint("parent_id", "child_id", name="unique_parent_child"),
    )
