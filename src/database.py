import os
from dotenv import load_dotenv
from sqlalchemy import event
from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

load_dotenv()

DB_URL = os.getenv("DB_URL")

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
