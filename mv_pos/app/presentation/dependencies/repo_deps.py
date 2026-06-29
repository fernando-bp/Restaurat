from typing import AsyncGenerator

from app.infrastructure.repositories.sql_usuario_repository import SQLUsuarioRepository
from app.infrastructure.repositories.sql_ingrediente_repository import SQLIngredienteRepository

from app.infrastructure.database.connection import async_session

async def get_usuario_repository() -> AsyncGenerator:
    async with async_session() as session:
        yield SQLUsuarioRepository(session)

async def get_ingrediente_repository() -> AsyncGenerator:
    async with async_session() as session:
        yield SQLIngredienteRepository(session)
