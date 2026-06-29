from __future__ import annotations
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.inventario_repository import InventarioRepository
from app.domain.entities.inventario import Inventario
from app.infrastructure.database.models.inventario import InventarioORM


class InventarioRepoSQLAlchemy(InventarioRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def obtener_por_id(self, inventario_id: int) -> Inventario | None:
        query = select(InventarioORM).where(InventarioORM.id == inventario_id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return Inventario(
            id=orm.id,
            ingrediente_id=orm.ingrediente_id,
            stock_actual=float(orm.stock_actual),
            stock_minimo=float(orm.stock_minimo),
            stock_maximo=float(orm.stock_maximo) if orm.stock_maximo is not None else None,
            ubicacion=orm.ubicacion,
        )

    async def obtener_por_ingrediente(self, ingrediente_id: int) -> Inventario | None:
        query = select(InventarioORM).where(InventarioORM.ingrediente_id == ingrediente_id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return Inventario(
            id=orm.id,
            ingrediente_id=orm.ingrediente_id,
            stock_actual=float(orm.stock_actual),
            stock_minimo=float(orm.stock_minimo),
            stock_maximo=float(orm.stock_maximo) if orm.stock_maximo is not None else None,
            ubicacion=orm.ubicacion,
        )

    async def listar(self) -> list[Inventario]:
        query = select(InventarioORM)
        result = await self.session.execute(query)
        rows = result.scalars().all()
        return [
            Inventario(
                id=row.id,
                ingrediente_id=row.ingrediente_id,
                stock_actual=float(row.stock_actual),
                stock_minimo=float(row.stock_minimo),
                stock_maximo=float(row.stock_maximo) if row.stock_maximo is not None else None,
                ubicacion=row.ubicacion,
            )
            for row in rows
        ]

    async def guardar(self, inventario: Inventario) -> Inventario:
        if inventario.id is None:
            raise NotImplementedError('Crear inventario no implementado en este repo')

        query = select(InventarioORM).where(InventarioORM.id == inventario.id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if orm:
            orm.stock_actual = inventario.stock_actual
            orm.stock_minimo = inventario.stock_minimo
            orm.stock_maximo = inventario.stock_maximo
            orm.ubicacion = inventario.ubicacion
            await self.session.commit()
        return inventario

    async def eliminar(self, inventario_id: int) -> None:
        query = select(InventarioORM).where(InventarioORM.id == inventario_id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)
            await self.session.commit()
