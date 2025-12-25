from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.family_service import FamilyService

router = APIRouter()


@router.get("/{person_id}/ancestors")
async def get_ancestors(
    person_id: UUID,
    generations: int = Query(3, le=10, description="Number of generations"),
    db: AsyncSession = Depends(get_db)
):
    """Get ancestor tree up to N generations."""
    service = FamilyService(db)
    tree = await service.get_ancestors(person_id, generations)

    if not tree:
        raise HTTPException(status_code=404, detail="Person not found")

    return tree.to_dict()


@router.get("/{person_id}/descendants")
async def get_descendants(
    person_id: UUID,
    generations: int = Query(3, le=10, description="Number of generations"),
    db: AsyncSession = Depends(get_db)
):
    """Get descendant tree down to N generations."""
    service = FamilyService(db)
    tree = await service.get_descendants(person_id, generations)

    if not tree:
        raise HTTPException(status_code=404, detail="Person not found")

    return tree.to_dict()


@router.get("/{person_id}/tree")
async def get_full_tree(
    person_id: UUID,
    ancestor_gens: int = Query(2, le=5, alias="ancestorGenerations"),
    descendant_gens: int = Query(2, le=5, alias="descendantGenerations"),
    db: AsyncSession = Depends(get_db)
):
    """Get combined ancestor and descendant tree centered on a person."""
    service = FamilyService(db)
    tree = await service.get_full_tree(person_id, ancestor_gens, descendant_gens)

    if not tree:
        raise HTTPException(status_code=404, detail="Person not found")

    return tree
