from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.orden_repository import OrdenRepository
from app.domain.entities.orden import Orden
from app.infrastructure.database.models.mesa import OrdenORM
from app.infrastructure.database.models.orden_item import OrdenItemORM
from app.infrastructure.mappers.orden_mapper import orden_from_orm, orm_from_orden


class OrdenRepoSQLAlchemy(OrdenRepository):
    def __init__(self, session: AsyncSession, restaurante_id: int = 1):
        self.session = session
        self.restaurante_id = restaurante_id

    async def obtener_por_id(self, orden_id: int) -> Orden | None:
        query = select(OrdenORM).where(
            OrdenORM.id == orden_id,
            OrdenORM.restaurante_id == self.restaurante_id,
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return orden_from_orm(orm) if orm else None

    async def listar_por_mesa(self, mesa_id: int) -> list[Orden]:
        query = select(OrdenORM).where(
            OrdenORM.mesa_id == mesa_id,
            OrdenORM.restaurante_id == self.restaurante_id,
            OrdenORM.estado.in_(['abierta', 'en_preparacion', 'lista']),
        )
        result = await self.session.execute(query)
        rows = result.scalars().all()
        return [orden_from_orm(row) for row in rows]

    async def obtener_orden_activa_por_mesa(self, mesa_id: int) -> Orden | None:
        query = select(OrdenORM).where(
            OrdenORM.mesa_id == mesa_id,
            OrdenORM.restaurante_id == self.restaurante_id,
            OrdenORM.estado.in_(['abierta', 'en_preparacion', 'lista']),
        ).limit(1)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return orden_from_orm(orm) if orm else None

    async def guardar(self, orden: Orden) -> Orden:
        if orden.id is None:
            data = orm_from_orden(orden)
            data.pop("id", None)
            orm = OrdenORM(**data)
            orm.restaurante_id = self.restaurante_id
            self.session.add(orm)
            await self.session.commit()
            await self.session.refresh(orm)

            if orden.items:
                item_orms = []
                for item in orden.items:
                    if item.id is None:
                        item_orm = OrdenItemORM(
                            orden_id=orm.id,
                            receta_id=item.receta_id,
                            cantidad=item.cantidad,
                            precio_unitario=item.precio_unitario,
                            estado=item.estado,
                            notas=item.observaciones,
                        )
                        item_orms.append(item_orm)
                if item_orms:
                    self.session.add_all(item_orms)
                    await self.session.commit()
                    await self.session.refresh(orm)
            return orden_from_orm(orm)
        else:
            query = select(OrdenORM).where(
                OrdenORM.id == orden.id,
                OrdenORM.restaurante_id == self.restaurante_id,
            )
            result = await self.session.execute(query)
            orm = result.scalar_one_or_none()
            if orm:
                orm.estado = orden.estado.value
                orm.num_comensales = orden.num_comensales
                orm.notas_generales = orden.notas_generales
                orm.hora_confirmacion = orden.hora_confirmacion
                orm.hora_cierre = orden.hora_cierre
                orm.total_bruto = orden.total_bruto
                orm.total_descuento = orden.total_descuento
                orm.total_iva = orden.total_iva
                orm.total_neto = orden.total_neto

                if orden.items:
                    for item in orden.items:
                        if item.id is None:
                            item_orm = OrdenItemORM(
                                orden_id=orm.id,
                                receta_id=item.receta_id,
                                cantidad=item.cantidad,
                                precio_unitario=item.precio_unitario,
                                estado=item.estado,
                                notas=item.observaciones,
                            )
                            self.session.add(item_orm)

                await self.session.commit()
                await self.session.refresh(orm)
                return orden_from_orm(orm)
            return orden

    async def eliminar(self, orden_id: int) -> None:
        orden = await self.obtener_por_id(orden_id)
        if orden:
            orden.estado = 'cancelada'
            await self.guardar(orden)
