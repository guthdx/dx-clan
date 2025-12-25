from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.relationship_service import RelationshipService
from app.schemas.genealogy import MarriageCreate, ParentChildCreate

router = APIRouter()


# Response schemas
class MarriageResponse(BaseModel):
    id: UUID
    spouse1_id: UUID = Field(alias="spouse1Id")
    spouse2_id: UUID = Field(alias="spouse2Id")
    marriage_order: int = Field(alias="marriageOrder")
    marriage_year: int | None = Field(None, alias="marriageYear")
    notes: str | None = None

    class Config:
        from_attributes = True
        populate_by_name = True


class ParentChildResponse(BaseModel):
    id: UUID
    parent_id: UUID = Field(alias="parentId")
    child_id: UUID = Field(alias="childId")
    relationship_type: str = Field(alias="relationshipType")

    class Config:
        from_attributes = True
        populate_by_name = True


# Marriage endpoints
@router.post("/marriages", response_model=MarriageResponse, status_code=status.HTTP_201_CREATED)
async def create_marriage(
    data: MarriageCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a marriage between two persons."""
    service = RelationshipService(db)
    try:
        marriage = await service.create_marriage(data)
        return MarriageResponse(
            id=marriage.id,
            spouse1Id=marriage.spouse1_id,
            spouse2Id=marriage.spouse2_id,
            marriageOrder=marriage.marriage_order,
            marriageYear=marriage.marriage_year,
            notes=marriage.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/marriages/{marriage_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_marriage(
    marriage_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a marriage by ID."""
    service = RelationshipService(db)
    deleted = await service.delete_marriage(marriage_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Marriage not found")


@router.delete("/marriages/by-spouses/{spouse1_id}/{spouse2_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_marriage_by_spouses(
    spouse1_id: UUID,
    spouse2_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a marriage by spouse IDs."""
    service = RelationshipService(db)
    deleted = await service.delete_marriage_by_spouses(spouse1_id, spouse2_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Marriage not found")


# Parent-child endpoints
@router.post("/parent-child", response_model=ParentChildResponse, status_code=status.HTTP_201_CREATED)
async def create_parent_child(
    data: ParentChildCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a parent-child relationship."""
    service = RelationshipService(db)
    try:
        relationship = await service.create_parent_child(data)
        return ParentChildResponse(
            id=relationship.id,
            parentId=relationship.parent_id,
            childId=relationship.child_id,
            relationshipType=relationship.relationship_type
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/parent-child/{relationship_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parent_child(
    relationship_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a parent-child relationship by ID."""
    service = RelationshipService(db)
    deleted = await service.delete_parent_child(relationship_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Relationship not found")


@router.delete("/parent-child/by-persons/{parent_id}/{child_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_parent_child_by_persons(
    parent_id: UUID,
    child_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete a parent-child relationship by person IDs."""
    service = RelationshipService(db)
    deleted = await service.delete_parent_child_by_persons(parent_id, child_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Relationship not found")
