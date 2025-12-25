from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.person_service import PersonService
from app.schemas.genealogy import (
    PersonDetail, PersonSummary, SearchResponse, SearchResult,
    AliasSchema, SpouseInfo, PersonCreate, PersonUpdate
)

router = APIRouter()


def format_lifespan(birth: int | None, death: int | None) -> str | None:
    """Format birth/death years as lifespan string."""
    if birth and death:
        return f"{birth} - {death}"
    elif birth:
        return f"b. {birth}"
    elif death:
        return f"d. {death}"
    return None


def person_to_summary(person) -> PersonSummary:
    """Convert Person model to PersonSummary schema."""
    return PersonSummary(
        id=person.id,
        displayName=person.display_name,
        birthYear=person.birth_year,
        deathYear=person.death_year,
        lifespan=format_lifespan(person.birth_year, person.death_year)
    )


@router.get("/search", response_model=SearchResponse)
async def search_persons(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, le=100, description="Maximum results"),
    db: AsyncSession = Depends(get_db)
):
    """Search persons by name with autocomplete support."""
    service = PersonService(db)
    persons = await service.search(q, limit)

    results = [
        SearchResult(
            id=p.id,
            displayName=p.display_name,
            matchedAlias=None,  # Could enhance to show which alias matched
            lifespan=format_lifespan(p.birth_year, p.death_year)
        )
        for p in persons
    ]

    return SearchResponse(query=q, results=results, totalCount=len(results))


@router.get("/founding-ancestors", response_model=List[PersonSummary])
async def get_founding_ancestors(
    limit: int = Query(12, le=50, description="Maximum results"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get founding ancestors - root persons with no parents in the database.
    These are the earliest known ancestors in the family tree.
    """
    service = PersonService(db)
    persons = await service.get_founding_ancestors(limit)

    return [person_to_summary(p) for p in persons]


@router.get("/{person_id}", response_model=PersonDetail)
async def get_person(
    person_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get full person details with relationships."""
    service = PersonService(db)
    person = await service.get_by_id(person_id)

    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Get related data
    spouses = await service.get_spouses(person_id)
    children = await service.get_children(person_id)
    parents = await service.get_parents(person_id)

    # Build aliases list
    aliases = [
        AliasSchema(
            id=a.id,
            aliasName=a.alias_name,
            aliasType=a.alias_type,
            isPrimary=a.is_primary or False
        )
        for a in (person.aliases or [])
    ]

    # Build spouse info
    spouse_infos = [
        SpouseInfo(
            person=person_to_summary(s),
            marriageOrder=1,  # Could get from marriage record
            marriageYear=None
        )
        for s in spouses
    ]

    return PersonDetail(
        id=person.id,
        displayName=person.display_name,
        birthYear=person.birth_year,
        birthYearCirca=person.birth_year_circa or False,
        deathYear=person.death_year,
        deathYearCirca=person.death_year_circa or False,
        gender=person.gender,
        tribalAffiliation=person.tribal_affiliation,
        notes=person.notes,
        generation=person.generation,
        lifespan=format_lifespan(person.birth_year, person.death_year),
        aliases=aliases,
        spouses=spouse_infos,
        parents=[person_to_summary(p) for p in parents],
        children=[person_to_summary(c) for c in children],
        createdAt=person.created_at,
        updatedAt=person.updated_at
    )


@router.get("", response_model=List[PersonSummary])
async def list_persons(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """List all persons with pagination."""
    service = PersonService(db)
    persons, total = await service.list_all(limit, offset)

    return [person_to_summary(p) for p in persons]


@router.post("", response_model=PersonDetail, status_code=status.HTTP_201_CREATED)
async def create_person(
    data: PersonCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new person."""
    service = PersonService(db)
    person = await service.create(data)

    # Fetch full details for response
    return await get_person(person.id, db)


@router.put("/{person_id}", response_model=PersonDetail)
async def update_person(
    person_id: UUID,
    data: PersonUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing person."""
    service = PersonService(db)
    person = await service.update(person_id, data)

    if not person:
        raise HTTPException(status_code=404, detail="Person not found")

    # Fetch full details for response
    return await get_person(person.id, db)


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_person(
    person_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a person and all related records."""
    service = PersonService(db)
    deleted = await service.delete(person_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Person not found")


@router.post("/{person_id}/aliases", response_model=AliasSchema, status_code=status.HTTP_201_CREATED)
async def add_alias(
    person_id: UUID,
    alias_name: str = Query(..., min_length=1),
    alias_type: str = Query("alternate"),
    db: AsyncSession = Depends(get_db)
):
    """Add an alias to a person."""
    service = PersonService(db)
    alias = await service.add_alias(person_id, alias_name, alias_type)

    if not alias:
        raise HTTPException(status_code=404, detail="Person not found")

    return AliasSchema(
        id=alias.id,
        aliasName=alias.alias_name,
        aliasType=alias.alias_type,
        isPrimary=alias.is_primary or False
    )


@router.delete("/{person_id}/aliases/{alias_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_alias(
    person_id: UUID,
    alias_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Remove an alias from a person."""
    service = PersonService(db)
    deleted = await service.remove_alias(alias_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Alias not found")
