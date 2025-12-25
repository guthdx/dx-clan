from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("Starting DX Clan Genealogy API...")
    yield
    # Shutdown
    print("Shutting down DX Clan Genealogy API...")


app = FastAPI(
    title="DX Clan Genealogy API",
    description="API for Ducheneaux family genealogy database",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "DX Clan Genealogy API",
        "version": "1.0.0",
        "docs": "/docs",
    }
