from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.orden_item_repository import OrdenItemRepository
from app.domain.entities.orden_item import OrdenItem
from app.infrastructure.database.models.orden_item import OrdenItemORM


class OrdenItemRepoSQLAlchemy(OrdenItemRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def obtener_por_id(self, orden_item_id: int) -> OrdenItem | None:
        query = select(OrdenItemORM).where(OrdenItemORM.id == orden_item_id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return OrdenItem(
            id=orm.id,
            orden_id=orm.orden_id,
            receta_id=orm.receta_id,
            cantidad=orm.cantidad,
            precio_unitario=int(orm.precio_unitario),
            estado=orm.estado,
            observaciones=orm.notas,
        )

    async def listar_por_orden(self, orden_id: int) -> list[OrdenItem]:
        query = select(OrdenItemORM).where(OrdenItemORM.orden_id == orden_id)
        result = await self.session.execute(query)
        items = result.scalars().all()
        return [
            OrdenItem(
                id=item.id,
                orden_id=item.orden_id,
                receta_id=item.receta_id,
                cantidad=item.cantidad,
                precio_unitario=int(item.precio_unitario),
                estado=item.estado,
                observaciones=item.notas,
            )
            for item in items
        ]

    async def guardar(self, orden_item: OrdenItem) -> OrdenItem:
        if orden_item.id is None:
            orm = OrdenItemORM(
                orden_id=orden_item.orden_id,
                receta_id=orden_item.receta_id,
                cantidad=orden_item.cantidad,
                precio_unitario=orden_item.precio_unitario,
                estado=orden_item.estado,
                notas=orden_item.observaciones,
            )
            self.session.add(orm)
            await self.session.commit()
            await self.session.refresh(orm)
            orden_item.id = orm.id
            return orden_item

        query = select(OrdenItemORM).where(OrdenItemORM.id == orden_item.id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if orm:
            orm.cantidad = orden_item.cantidad
            orm.precio_unitario = orden_item.precio_unitario
            orm.estado = orden_item.estado
            orm.notas = orden_item.observaciones
            await self.session.commit()
        return orden_item

    async def eliminar(self, orden_item_id: int) -> None:
        query = select(OrdenItemORM).where(OrdenItemORM.id == orden_item_id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)
            await self.session.commit()
