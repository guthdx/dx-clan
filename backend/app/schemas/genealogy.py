from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class AliasSchema(BaseModel):
    id: UUID
    alias_name: str = Field(alias="aliasName")
    alias_type: Optional[str] = Field(None, alias="aliasType")
    is_primary: bool = Field(alias="isPrimary", default=False)

    class Config:
        from_attributes = True
        populate_by_name = True


class PersonSummary(BaseModel):
    id: UUID
    display_name: str = Field(alias="displayName")
    birth_year: Optional[int] = Field(None, alias="birthYear")
    death_year: Optional[int] = Field(None, alias="deathYear")
    lifespan: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class SpouseInfo(BaseModel):
    person: PersonSummary
    marriage_order: int = Field(alias="marriageOrder", default=1)
    marriage_year: Optional[int] = Field(None, alias="marriageYear")

    class Config:
        populate_by_name = True


class PersonDetail(BaseModel):
    id: UUID
    display_name: str = Field(alias="displayName")
    birth_year: Optional[int] = Field(None, alias="birthYear")
    birth_year_circa: bool = Field(False, alias="birthYearCirca")
    death_year: Optional[int] = Field(None, alias="deathYear")
    death_year_circa: bool = Field(False, alias="deathYearCirca")
    gender: Optional[str] = None
    tribal_affiliation: Optional[str] = Field(None, alias="tribalAffiliation")
    notes: Optional[str] = None
    generation: Optional[int] = None
    lifespan: Optional[str] = None
    aliases: List[AliasSchema] = []
    spouses: List[SpouseInfo] = []
    parents: List[PersonSummary] = []
    children: List[PersonSummary] = []
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")

    class Config:
        from_attributes = True
        populate_by_name = True


class SearchResult(BaseModel):
    id: UUID
    display_name: str = Field(alias="displayName")
    matched_alias: Optional[str] = Field(None, alias="matchedAlias")
    lifespan: Optional[str] = None

    class Config:
        populate_by_name = True


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_count: int = Field(alias="totalCount", default=0)

    class Config:
        populate_by_name = True


class TreeNode(BaseModel):
    person: PersonSummary
    spouses: List[PersonSummary] = []
    children: List["TreeNode"] = []
    parents: List["TreeNode"] = []
    expanded: bool = False

    class Config:
        populate_by_name = True


# Request schemas for create/update
class PersonCreate(BaseModel):
    display_name: str = Field(alias="displayName")
    birth_year: Optional[int] = Field(None, alias="birthYear")
    birth_year_circa: bool = Field(False, alias="birthYearCirca")
    death_year: Optional[int] = Field(None, alias="deathYear")
    death_year_circa: bool = Field(False, alias="deathYearCirca")
    gender: Optional[str] = None
    tribal_affiliation: Optional[str] = Field(None, alias="tribalAffiliation")
    notes: Optional[str] = None
    generation: Optional[int] = None
    aliases: List[str] = []

    class Config:
        populate_by_name = True


class PersonUpdate(BaseModel):
    display_name: Optional[str] = Field(None, alias="displayName")
    birth_year: Optional[int] = Field(None, alias="birthYear")
    birth_year_circa: Optional[bool] = Field(None, alias="birthYearCirca")
    death_year: Optional[int] = Field(None, alias="deathYear")
    death_year_circa: Optional[bool] = Field(None, alias="deathYearCirca")
    gender: Optional[str] = None
    tribal_affiliation: Optional[str] = Field(None, alias="tribalAffiliation")
    notes: Optional[str] = None
    generation: Optional[int] = None

    class Config:
        populate_by_name = True


class MarriageCreate(BaseModel):
    spouse1_id: UUID = Field(alias="spouse1Id")
    spouse2_id: UUID = Field(alias="spouse2Id")
    marriage_order: int = Field(alias="marriageOrder", default=1)
    marriage_year: Optional[int] = Field(None, alias="marriageYear")
    notes: Optional[str] = None

    class Config:
        populate_by_name = True


class ParentChildCreate(BaseModel):
    parent_id: UUID = Field(alias="parentId")
    child_id: UUID = Field(alias="childId")
    relationship_type: str = Field(alias="relationshipType", default="biological")

    class Config:
        populate_by_name = True
