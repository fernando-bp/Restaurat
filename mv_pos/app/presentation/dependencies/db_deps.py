from typing import AsyncGenerator

from app.infrastructure.database.connection import async_session

async def get_db_session() -> AsyncGenerator:
    """Provee una sesión de base de datos async por request."""
    async with async_session() as session:
        yield session
