"""Person service for genealogy database."""

from uuid import UUID
from typing import Optional

from sqlalchemy import select, func, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Person, PersonAlias, Marriage, ParentChild
from app.schemas.genealogy import PersonCreate, PersonUpdate


class PersonService:
    """Service for person-related operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def search(self, query: str, limit: int = 20, offset: int = 0) -> list[Person]:
        """
        Search for persons by name or alias.
        Uses case-insensitive LIKE matching.
        """
        if not query or len(query) < 2:
            return []

        search_pattern = f"%{query}%"

        # Search in display_name and aliases
        stmt = (
            select(Person)
            .outerjoin(PersonAlias)
            .where(
                or_(
                    Person.display_name.ilike(search_pattern),
                    PersonAlias.alias_name.ilike(search_pattern)
                )
            )
            .distinct()
            .order_by(Person.display_name)
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, person_id: UUID) -> Optional[Person]:
        """Get a person by ID with all relationships loaded."""
        stmt = (
            select(Person)
            .options(
                selectinload(Person.aliases),
                selectinload(Person.marriages_as_spouse1),
                selectinload(Person.marriages_as_spouse2),
                selectinload(Person.children_as_parent),
                selectinload(Person.parents_as_child),
            )
            .where(Person.id == person_id)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, limit: int = 50, offset: int = 0) -> tuple[list[Person], int]:
        """List all persons with pagination."""
        # Get total count
        count_stmt = select(func.count(Person.id))
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar()

        # Get persons
        stmt = (
            select(Person)
            .order_by(Person.display_name)
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(stmt)
        persons = list(result.scalars().all())

        return persons, total

    async def get_spouses(self, person_id: UUID) -> list[Person]:
        """Get all spouses of a person."""
        # Get marriages where person is either spouse
        stmt = (
            select(Marriage)
            .where(
                or_(
                    Marriage.spouse1_id == person_id,
                    Marriage.spouse2_id == person_id
                )
            )
            .order_by(Marriage.marriage_order)
        )

        result = await self.session.execute(stmt)
        marriages = result.scalars().all()

        spouses = []
        for marriage in marriages:
            spouse_id = marriage.spouse2_id if marriage.spouse1_id == person_id else marriage.spouse1_id
            spouse = await self.session.get(Person, spouse_id)
            if spouse:
                spouses.append(spouse)

        return spouses

    async def get_children(self, person_id: UUID) -> list[Person]:
        """Get all children of a person."""
        stmt = (
            select(Person)
            .join(ParentChild, ParentChild.child_id == Person.id)
            .where(ParentChild.parent_id == person_id)
            .order_by(Person.birth_year.nullslast(), Person.display_name)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_parents(self, person_id: UUID) -> list[Person]:
        """Get all parents of a person."""
        stmt = (
            select(Person)
            .join(ParentChild, ParentChild.parent_id == Person.id)
            .where(ParentChild.child_id == person_id)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_siblings(self, person_id: UUID) -> list[Person]:
        """Get all siblings of a person (share at least one parent)."""
        # First get parents
        parents = await self.get_parents(person_id)
        if not parents:
            return []

        parent_ids = [p.id for p in parents]

        # Get all children of these parents except the person themselves
        stmt = (
            select(Person)
            .join(ParentChild, ParentChild.child_id == Person.id)
            .where(
                ParentChild.parent_id.in_(parent_ids),
                Person.id != person_id
            )
            .distinct()
            .order_by(Person.birth_year.nullslast(), Person.display_name)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, data: PersonCreate) -> Person:
        """Create a new person with optional aliases."""
        person = Person(
            display_name=data.display_name,
            birth_year=data.birth_year,
            birth_year_circa=data.birth_year_circa,
            death_year=data.death_year,
            death_year_circa=data.death_year_circa,
            gender=data.gender,
            tribal_affiliation=data.tribal_affiliation,
            notes=data.notes,
            generation=data.generation,
        )
        self.session.add(person)
        await self.session.flush()

        # Add aliases if provided
        for alias_name in data.aliases:
            alias = PersonAlias(
                person_id=person.id,
                alias_name=alias_name,
                alias_type="alternate",
                is_primary=False
            )
            self.session.add(alias)

        await self.session.commit()
        await self.session.refresh(person)
        return person

    async def update(self, person_id: UUID, data: PersonUpdate) -> Optional[Person]:
        """Update an existing person."""
        person = await self.get_by_id(person_id)
        if not person:
            return None

        # Update only provided fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(person, field, value)

        await self.session.commit()
        await self.session.refresh(person)
        return person

    async def delete(self, person_id: UUID) -> bool:
        """Delete a person and all related records (cascade)."""
        person = await self.get_by_id(person_id)
        if not person:
            return False

        await self.session.delete(person)
        await self.session.commit()
        return True

    async def add_alias(self, person_id: UUID, alias_name: str, alias_type: str = "alternate") -> Optional[PersonAlias]:
        """Add an alias to a person."""
        person = await self.get_by_id(person_id)
        if not person:
            return None

        alias = PersonAlias(
            person_id=person_id,
            alias_name=alias_name,
            alias_type=alias_type,
            is_primary=False
        )
        self.session.add(alias)
        await self.session.commit()
        await self.session.refresh(alias)
        return alias

    async def remove_alias(self, alias_id: UUID) -> bool:
        """Remove an alias."""
        stmt = delete(PersonAlias).where(PersonAlias.id == alias_id)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
