import uuid
from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Person(Base):
    __tablename__ = "persons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    display_name = Column(String(255), nullable=False, index=True)
    birth_year = Column(Integer, nullable=True)
    birth_year_circa = Column(Boolean, default=False)
    death_year = Column(Integer, nullable=True)
    death_year_circa = Column(Boolean, default=False)
    gender = Column(String(20), nullable=True)  # 'male', 'female', 'unknown'
    tribal_affiliation = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    generation = Column(Integer, nullable=True)  # Generation number from source data
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    aliases = relationship(
        "PersonAlias",
        back_populates="person",
        cascade="all, delete-orphan"
    )
    marriages_as_spouse1 = relationship(
        "Marriage",
        foreign_keys="Marriage.spouse1_id",
        back_populates="spouse1",
        cascade="all, delete-orphan"
    )
    marriages_as_spouse2 = relationship(
        "Marriage",
        foreign_keys="Marriage.spouse2_id",
        back_populates="spouse2",
        cascade="all, delete-orphan"
    )
    children_as_parent = relationship(
        "ParentChild",
        foreign_keys="ParentChild.parent_id",
        back_populates="parent",
        cascade="all, delete-orphan"
    )
    parents_as_child = relationship(
        "ParentChild",
        foreign_keys="ParentChild.child_id",
        back_populates="child",
        cascade="all, delete-orphan"
    )
    sources = relationship(
        "Source",
        back_populates="person",
        cascade="all, delete-orphan"
    )

    # Full-text search index
    __table_args__ = (
        Index('idx_persons_name_search', 'display_name', postgresql_using='gin',
              postgresql_ops={'display_name': 'gin_trgm_ops'}),
    )

    @property
    def lifespan(self) -> str:
        """Format lifespan string"""
        parts = []
        if self.birth_year:
            prefix = "ca " if self.birth_year_circa else ""
            parts.append(f"{prefix}{self.birth_year}")
        else:
            parts.append("?")

        if self.death_year:
            prefix = "ca " if self.death_year_circa else ""
            parts.append(f"{prefix}{self.death_year}")
        elif self.birth_year:
            parts.append("?")

        return " - ".join(parts) if len(parts) > 1 else parts[0] if parts else ""
