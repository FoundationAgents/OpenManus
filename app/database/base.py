from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import config
from app.logger import logger

# Construct PostgreSQL URL from config
# Prioritize db_url if provided, otherwise construct from individual components
DB_URL = getattr(config.postgresql, 'db_url', None)
if not DB_URL:
    db_user = config.postgresql.user
    db_password = config.postgresql.password
    db_host = config.postgresql.host
    db_port = config.postgresql.port
    db_name = config.postgresql.db_name
    DB_URL = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

try:
    engine = create_async_engine(DB_URL, echo=False) # Set echo=True for SQL logging
except Exception as e:
    logger.error(f"Failed to create async database engine for URL '{DB_URL}': {e}")
    # Fallback or raise critical error
    engine = None

SessionLocal = None
if engine:
    try:
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False # Important for async sessions
        )
    except Exception as e:
        logger.error(f"Failed to create sessionmaker: {e}")
        SessionLocal = None

Base = declarative_base()

async def get_db() -> AsyncSession:
    if SessionLocal is None:
        logger.error("Database session (SessionLocal) is not initialized. Check database engine connection.")
        raise RuntimeError("Database session not initialized.")

    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()

async def init_db():
    """
    Initializes the database by creating all tables defined by Base.metadata.
    This should be called once when the application starts if tables don't exist.
    """
    if engine is None:
        logger.error("Database engine is not initialized. Cannot initialize database tables.")
        return

    async with engine.begin() as conn:
        try:
            # For now, we are not dropping tables. In development, you might want to.
            # await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized/checked successfully.")
        except Exception as e:
            logger.error(f"Error initializing database tables: {e}")
            # Depending on the error, you might want to handle it more gracefully or raise it

# To use init_db, you might call it in your main application startup:
# asyncio.run(init_db())
# Or, if in an async context:
# await init_db()
# Alembic is the preferred way for managing schema migrations in production.
# This init_db is more for development and initial setup.
