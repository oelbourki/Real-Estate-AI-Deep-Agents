"""PostgreSQL checkpointer setup for LangGraph (async)."""

import logging

from backend.config.settings import settings

logger = logging.getLogger(__name__)


def is_postgres_configured() -> bool:
    """Return True if Postgres is configured for checkpoints (host, db, user, and password set)."""
    return bool(
        settings.postgres_host
        and settings.postgres_db
        and settings.postgres_user
        and (
            settings.postgres_password is not None and settings.postgres_password != ""
        )
    )


async def create_postgres_checkpointer():
    """
    Create AsyncPostgresSaver and run setup. Call from async context (e.g. FastAPI lifespan).

    Returns:
        Tuple of (connection_pool, checkpointer) or (None, None) if not configured or on error.
    """
    if not is_postgres_configured():
        logger.info("PostgreSQL not configured; using in-memory checkpointer")
        return None, None

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg_pool import AsyncConnectionPool
        from urllib.parse import quote_plus
    except ImportError as e:
        logger.info(
            "PostgreSQL checkpointer not available (install langgraph-checkpoint-postgres, psycopg, psycopg_pool); using in-memory: %s",
            e,
        )
        return None, None

    try:
        user = quote_plus(settings.postgres_user)
        password = quote_plus(settings.postgres_password or "")
        host = settings.postgres_host
        port = settings.postgres_port
        db = settings.postgres_db
        connection_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
        logger.info(
            "Connecting to PostgreSQL at %s:%s/%s (checkpointer pool)",
            host,
            port,
            db,
        )

        pool = AsyncConnectionPool(
            connection_url,
            open=False,
            max_size=settings.postgres_pool_size,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        await pool.open()

        checkpointer = AsyncPostgresSaver(pool)
        await checkpointer.setup()

        logger.info(
            "PostgreSQL checkpointer ready: %s:%s/%s",
            host,
            port,
            db,
        )
        return pool, checkpointer
    except Exception as e:
        logger.warning(
            "Failed to create PostgreSQL checkpointer: %s; using in-memory",
            e,
            exc_info=True,
        )
        return None, None
