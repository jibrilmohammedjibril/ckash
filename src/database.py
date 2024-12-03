import os
from urllib.parse import quote_plus
from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

# Database configuration
#password = quote_plus("Halifas@2001")
#DB_URL = f"postgresql+asyncpg://postgres:{password}@localhost:5432/ckash"
DB_URL = os.getenv("DB_URL")
# Create async engine
if DB_URL is None:
    password = quote_plus("Halifas@2001")
    DB_URL = f"postgresql+asyncpg://postgres:{password}@localhost:5432/ckash"


async_engine = create_async_engine(DB_URL, echo=True)

# Create sessionmaker bound to the async engine
SessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# Initialize the database
async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


# Dependency to get a database session
async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
