from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.ingrediente_repository import IngredienteRepository
from app.domain.entities.ingrediente import Ingrediente
from app.infrastructure.database.models.ingrediente import IngredienteORM


class IngredienteRepoSQLAlchemy(IngredienteRepository):
    def __init__(self, session: AsyncSession, restaurante_id: int = 1):
        self.session = session
        self.restaurante_id = restaurante_id

    async def obtener_por_id(self, ingrediente_id: int) -> Ingrediente | None:
        query = select(IngredienteORM).where(
            IngredienteORM.id == ingrediente_id,
            IngredienteORM.restaurante_id == self.restaurante_id,
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return Ingrediente(
            id=orm.id,
            nombre=orm.nombre,
            unidad_base_id=orm.unidad_base_id,
            precio_unitario=int(orm.precio_unitario),
            categoria=orm.categoria,
            activo=orm.activo,
        )

    async def listar(self, disponibles: bool | None = None) -> list[Ingrediente]:
        query = select(IngredienteORM).where(
            IngredienteORM.restaurante_id == self.restaurante_id
        )
        if disponibles is True:
            query = query.where(IngredienteORM.activo == True)
        result = await self.session.execute(query)
        rows = result.scalars().all()
        return [
            Ingrediente(
                id=row.id,
                nombre=row.nombre,
                unidad_base_id=row.unidad_base_id,
                precio_unitario=int(row.precio_unitario),
                categoria=row.categoria,
                activo=row.activo,
            )
            for row in rows
        ]

    async def guardar(self, ingrediente: Ingrediente) -> Ingrediente:
        raise NotImplementedError

    async def eliminar(self, ingrediente_id: int) -> None:
        query = select(IngredienteORM).where(
            IngredienteORM.id == ingrediente_id,
            IngredienteORM.restaurante_id == self.restaurante_id,
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)
            await self.session.commit()

    async def obtener_unidad_base_abreviatura(self, ingrediente_id: int) -> str | None:
        result = await self.session.execute(
            select(IngredienteORM).where(
                IngredienteORM.id == ingrediente_id,
                IngredienteORM.restaurante_id == self.restaurante_id,
            )
        )
        orm = result.scalar_one_or_none()
        if not orm or not orm.unidad:
            return None
        return orm.unidad.abreviatura
