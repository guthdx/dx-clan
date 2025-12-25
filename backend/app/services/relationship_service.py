"""Relationship service for genealogy database."""

from uuid import UUID
from typing import Optional

from sqlalchemy import select, or_, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Person, Marriage, ParentChild
from app.schemas.genealogy import MarriageCreate, ParentChildCreate


class RelationshipService:
    """Service for relationship-related operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Marriage operations
    async def create_marriage(self, data: MarriageCreate) -> Marriage:
        """Create a marriage between two persons."""
        # Verify both persons exist
        spouse1 = await self.session.get(Person, data.spouse1_id)
        spouse2 = await self.session.get(Person, data.spouse2_id)

        if not spouse1 or not spouse2:
            raise ValueError("One or both spouses not found")

        if data.spouse1_id == data.spouse2_id:
            raise ValueError("Cannot create marriage with same person")

        # Check if marriage already exists
        existing = await self.get_marriage(data.spouse1_id, data.spouse2_id)
        if existing:
            raise ValueError("Marriage already exists between these persons")

        marriage = Marriage(
            spouse1_id=data.spouse1_id,
            spouse2_id=data.spouse2_id,
            marriage_order=data.marriage_order,
            marriage_year=data.marriage_year,
            notes=data.notes
        )
        self.session.add(marriage)
        await self.session.commit()
        await self.session.refresh(marriage)
        return marriage

    async def get_marriage(self, spouse1_id: UUID, spouse2_id: UUID) -> Optional[Marriage]:
        """Get marriage between two persons (order-independent)."""
        stmt = select(Marriage).where(
            or_(
                and_(Marriage.spouse1_id == spouse1_id, Marriage.spouse2_id == spouse2_id),
                and_(Marriage.spouse1_id == spouse2_id, Marriage.spouse2_id == spouse1_id)
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_marriage_by_id(self, marriage_id: UUID) -> Optional[Marriage]:
        """Get marriage by ID."""
        return await self.session.get(Marriage, marriage_id)

    async def delete_marriage(self, marriage_id: UUID) -> bool:
        """Delete a marriage."""
        marriage = await self.get_marriage_by_id(marriage_id)
        if not marriage:
            return False

        await self.session.delete(marriage)
        await self.session.commit()
        return True

    async def delete_marriage_by_spouses(self, spouse1_id: UUID, spouse2_id: UUID) -> bool:
        """Delete a marriage by spouse IDs."""
        marriage = await self.get_marriage(spouse1_id, spouse2_id)
        if not marriage:
            return False

        await self.session.delete(marriage)
        await self.session.commit()
        return True

    # Parent-child operations
    async def create_parent_child(self, data: ParentChildCreate) -> ParentChild:
        """Create a parent-child relationship."""
        # Verify both persons exist
        parent = await self.session.get(Person, data.parent_id)
        child = await self.session.get(Person, data.child_id)

        if not parent or not child:
            raise ValueError("Parent or child not found")

        if data.parent_id == data.child_id:
            raise ValueError("Cannot create parent-child with same person")

        # Check if relationship already exists
        existing = await self.get_parent_child(data.parent_id, data.child_id)
        if existing:
            raise ValueError("Parent-child relationship already exists")

        relationship = ParentChild(
            parent_id=data.parent_id,
            child_id=data.child_id,
            relationship_type=data.relationship_type
        )
        self.session.add(relationship)
        await self.session.commit()
        await self.session.refresh(relationship)
        return relationship

    async def get_parent_child(self, parent_id: UUID, child_id: UUID) -> Optional[ParentChild]:
        """Get parent-child relationship."""
        stmt = select(ParentChild).where(
            and_(ParentChild.parent_id == parent_id, ParentChild.child_id == child_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_parent_child_by_id(self, relationship_id: UUID) -> Optional[ParentChild]:
        """Get parent-child relationship by ID."""
        return await self.session.get(ParentChild, relationship_id)

    async def delete_parent_child(self, relationship_id: UUID) -> bool:
        """Delete a parent-child relationship by ID."""
        relationship = await self.get_parent_child_by_id(relationship_id)
        if not relationship:
            return False

        await self.session.delete(relationship)
        await self.session.commit()
        return True

    async def delete_parent_child_by_persons(self, parent_id: UUID, child_id: UUID) -> bool:
        """Delete a parent-child relationship by person IDs."""
        relationship = await self.get_parent_child(parent_id, child_id)
        if not relationship:
            return False

        await self.session.delete(relationship)
        await self.session.commit()
        return True
