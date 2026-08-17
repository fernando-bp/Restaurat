from __future__ import annotations

from typing import AsyncGenerator

from app.infrastructure.database.connection import async_session


async def get_db_session() -> AsyncGenerator:
    async with async_session() as session:
        yield session


# Alias — in the shared DB approach the "control" session is the same DB.
get_control_db_session = get_db_session
