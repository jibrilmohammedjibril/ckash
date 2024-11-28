from fastapi import FastAPI
from .database import init_db
from .api import router
from sqlmodel import SQLModel
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Run any startup tasks
    await init_db()
    yield
    # Run any shutdown tasks if needed


# Initialize the FastAPI application
app = FastAPI(
    title="Ckash Fintech App",
    description="Engine behind Ckash for managing loans, utilities, and transactions",
    version="0.1",
    lifespan=lifespan,  # Attach the lifespan manager
)

# Include the routers from different app modules (authentication, notifications, etc.)
app.include_router(router)
