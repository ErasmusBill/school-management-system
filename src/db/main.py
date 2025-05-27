from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from src.config import Config

# Create SQLAlchemy declarative base
Base = declarative_base()

# Create async engine
database_url = Config.DATABASE_URL.replace(r'\x3a', ':') if r'\x3a' in Config.DATABASE_URL else Config.DATABASE_URL

async_engine = create_async_engine(
    database_url,
    echo=True,
    future=True,
    connect_args={"ssl": True} if "postgres" in database_url.lower() else {}
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

from src.db.models import *  # Import all models here

async def init_db():
    """Initialize database tables"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session():
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()