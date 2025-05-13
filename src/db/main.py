from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker # type: ignore
from sqlalchemy.orm import declarative_base # type: ignore
from src.config import Config

# Create SQLAlchemy declarative base
Base = declarative_base()

# Create async engine
async_engine = create_async_engine(
    Config.DATABASE_URL,
    echo=True,
    future=True,
    connect_args={"ssl": True} if Config.DATABASE_URL.startswith("postgres") else {}
)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

async def init_db():
    """Initialize database tables"""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_session() -> AsyncSession:
    """Dependency for getting async database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()