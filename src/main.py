from fastapi import FastAPI
from sqlalchemy import event

from .database import init_db, async_engine
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


@event.listens_for(async_engine.sync_engine, "connect")
def set_timezone(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("SET TIME ZONE 'UTC';")
    cursor.close()


# Initialize the FastAPI application
app = FastAPI(
    title="Ckash Fintech App",
    description="Engine behind Ckash for managing loans, utilities, and transactions",
    version="0.1",
    lifespan=lifespan,  # Attach the lifespan manager
)

# Include the routers from different app modules (authentication, notifications, etc.)
app.include_router(router)
