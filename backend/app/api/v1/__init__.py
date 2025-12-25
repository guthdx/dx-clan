from fastapi import APIRouter

from app.api.v1 import health, persons, families, relationships

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(persons.router, prefix="/persons", tags=["persons"])
api_router.include_router(families.router, prefix="/families", tags=["families"])
api_router.include_router(relationships.router, prefix="/relationships", tags=["relationships"])
