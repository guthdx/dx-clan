import uuid
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class PersonAlias(Base):
    __tablename__ = "person_aliases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    person_id = Column(
        UUID(as_uuid=True),
        ForeignKey("persons.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    alias_name = Column(String(255), nullable=False)
    alias_type = Column(String(50), nullable=True)  # 'nickname', 'alternate', 'tribal_name', 'married_name'
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    person = relationship("Person", back_populates="aliases")

    # Indexes
    __table_args__ = (
        Index('idx_aliases_name', 'alias_name'),
        Index('idx_aliases_name_search', 'alias_name', postgresql_using='gin',
              postgresql_ops={'alias_name': 'gin_trgm_ops'}),
    )
