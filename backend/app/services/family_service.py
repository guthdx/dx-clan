"""Family tree service for genealogy database."""

from uuid import UUID
from typing import Optional
from dataclasses import dataclass, field

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Person, Marriage, ParentChild


@dataclass
class TreeNode:
    """Represents a person in a family tree."""
    id: UUID
    display_name: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None
    generation: int = 0
    spouses: list['TreeNode'] = field(default_factory=list)
    children: list['TreeNode'] = field(default_factory=list)
    parents: list['TreeNode'] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "displayName": self.display_name,
            "birthYear": self.birth_year,
            "deathYear": self.death_year,
            "generation": self.generation,
            "spouses": [s.to_dict() for s in self.spouses] if self.spouses else [],
            "children": [c.to_dict() for c in self.children] if self.children else [],
            "parents": [p.to_dict() for p in self.parents] if self.parents else [],
        }


class FamilyService:
    """Service for family tree operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    def _person_to_node(self, person: Person, gen: int = 0) -> TreeNode:
        """Convert a Person to a TreeNode."""
        return TreeNode(
            id=person.id,
            display_name=person.display_name,
            birth_year=person.birth_year,
            death_year=person.death_year,
            generation=gen,
        )

    async def _get_spouses(self, person_id: UUID) -> list[Person]:
        """Get spouses of a person."""
        stmt = select(Marriage).where(
            or_(
                Marriage.spouse1_id == person_id,
                Marriage.spouse2_id == person_id
            )
        )
        result = await self.session.execute(stmt)
        marriages = result.scalars().all()

        spouses = []
        for m in marriages:
            spouse_id = m.spouse2_id if m.spouse1_id == person_id else m.spouse1_id
            spouse = await self.session.get(Person, spouse_id)
            if spouse:
                spouses.append(spouse)
        return spouses

    async def _get_parents(self, person_id: UUID) -> list[Person]:
        """Get parents of a person."""
        stmt = (
            select(Person)
            .join(ParentChild, ParentChild.parent_id == Person.id)
            .where(ParentChild.child_id == person_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _get_children(self, person_id: UUID) -> list[Person]:
        """Get children of a person."""
        stmt = (
            select(Person)
            .join(ParentChild, ParentChild.child_id == Person.id)
            .where(ParentChild.parent_id == person_id)
            .order_by(Person.birth_year.nullslast(), Person.display_name)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_ancestors(
        self, person_id: UUID, generations: int = 3, _visited: set = None
    ) -> Optional[TreeNode]:
        """
        Get ancestor tree for a person.
        Returns tree structure with parents recursively up to specified generations.
        """
        if _visited is None:
            _visited = set()

        if person_id in _visited or generations < 0:
            return None

        _visited.add(person_id)

        person = await self.session.get(Person, person_id)
        if not person:
            return None

        node = self._person_to_node(person, 0)

        # Add spouses (at same generation level)
        spouses = await self._get_spouses(person_id)
        node.spouses = [self._person_to_node(s, 0) for s in spouses]

        # Add parents (recursively)
        if generations > 0:
            parents = await self._get_parents(person_id)
            for parent in parents:
                parent_node = await self.get_ancestors(
                    parent.id, generations - 1, _visited.copy()
                )
                if parent_node:
                    parent_node.generation = 1  # Parent is one generation up
                    node.parents.append(parent_node)

        return node

    async def get_descendants(
        self, person_id: UUID, generations: int = 3, _visited: set = None
    ) -> Optional[TreeNode]:
        """
        Get descendant tree for a person.
        Returns tree structure with children recursively down to specified generations.
        """
        if _visited is None:
            _visited = set()

        if person_id in _visited or generations < 0:
            return None

        _visited.add(person_id)

        person = await self.session.get(Person, person_id)
        if not person:
            return None

        node = self._person_to_node(person, 0)

        # Add spouses (at same generation level)
        spouses = await self._get_spouses(person_id)
        node.spouses = [self._person_to_node(s, 0) for s in spouses]

        # Add children (recursively)
        if generations > 0:
            children = await self._get_children(person_id)
            for child in children:
                child_node = await self.get_descendants(
                    child.id, generations - 1, _visited.copy()
                )
                if child_node:
                    child_node.generation = 1  # Child is one generation down
                    node.children.append(child_node)

        return node

    async def get_full_tree(
        self, person_id: UUID, ancestor_gens: int = 2, descendant_gens: int = 2
    ) -> Optional[dict]:
        """
        Get a combined ancestor and descendant tree centered on a person.
        """
        person = await self.session.get(Person, person_id)
        if not person:
            return None

        ancestors = await self.get_ancestors(person_id, ancestor_gens)
        descendants = await self.get_descendants(person_id, descendant_gens)

        return {
            "person": {
                "id": str(person.id),
                "displayName": person.display_name,
                "birthYear": person.birth_year,
                "deathYear": person.death_year,
            },
            "ancestors": ancestors.to_dict() if ancestors else None,
            "descendants": descendants.to_dict() if descendants else None,
        }
