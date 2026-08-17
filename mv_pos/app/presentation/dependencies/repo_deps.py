from typing import AsyncGenerator

from app.infrastructure.repositories.usuario_repo_sqlalchemy import UsuarioRepoSQLAlchemy
from app.infrastructure.repositories.sql_ingrediente_repository import SQLIngredienteRepository

from app.infrastructure.database.control_connection import control_async_session


async def get_usuario_repository() -> AsyncGenerator:
    """
    Repositorio de usuarios sobre el control DB.

    NOTA: Este dep se usa en rutas de admin que no pasan por el flujo
    de tenant (ej: gestión de usuarios del control plane).
    Para usuarios dentro de un tenant, los routers crean el repo
    directamente con la sesión de get_db_session.
    """
    async with control_async_session() as session:
        yield UsuarioRepoSQLAlchemy(session)


async def get_ingrediente_repository() -> AsyncGenerator:
    """
    Este dep usa el control DB como fallback.
    Los routers de ingredientes por tenant lo crean con get_db_session.
    """
    async with control_async_session() as session:
        yield SQLIngredienteRepository(session)
