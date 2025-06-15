import datetime # Add this import
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Column, Integer, String, DateTime, Text # Ensure Text is imported

DATABASE_URL = "sqlite+aiosqlite:///./gui/backend/logs.db"

engine = create_async_engine(DATABASE_URL, echo=False) # Set echo to False for cleaner logs

class SQLBase(DeclarativeBase):
    pass

class LogEntry(SQLBase):
    __tablename__ = "log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    level: Mapped[str] = mapped_column(String(50))
    message: Mapped[str] = mapped_column(Text) # Use Text for potentially long messages
    logger_name: Mapped[str] = mapped_column(String(255), nullable=True)
    module: Mapped[str] = mapped_column(String(255), nullable=True)
    function: Mapped[str] = mapped_column(String(255), nullable=True)
    line: Mapped[int] = mapped_column(Integer, nullable=True)
    execution_id: Mapped[str] = mapped_column(String(255), nullable=True, index=True) # Add index for faster lookups

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLBase.metadata.create_all)

AsyncSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)

async def get_db() -> AsyncSession: # Return type should be AsyncSession, not just generator
    async with AsyncSessionLocal() as session:
        yield session
