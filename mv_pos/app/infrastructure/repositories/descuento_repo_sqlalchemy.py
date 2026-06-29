from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.descuento_repository import DescuentoRepository
from app.domain.entities.descuento import Descuento
from app.infrastructure.database.models.pago import DescuentoORM


class DescuentoRepoSQLAlchemy(DescuentoRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def obtener_por_id(self, descuento_id: int) -> Descuento | None:
        query = select(DescuentoORM).where(DescuentoORM.id == descuento_id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._from_orm(orm) if orm else None

    async def listar_por_orden(self, orden_id: int) -> list[Descuento]:
        query = select(DescuentoORM).where(DescuentoORM.orden_id == orden_id)
        result = await self.session.execute(query)
        rows = result.scalars().all()
        return [self._from_orm(row) for row in rows]

    async def guardar(self, descuento: Descuento) -> Descuento:
        if descuento.id is None:
            orm = DescuentoORM(
                orden_id=descuento.orden_id,
                porcentaje=descuento.porcentaje,
                monto=descuento.monto,
                motivo=descuento.motivo,
                autorizado_por=descuento.autorizado_por,
                requirio_pin=descuento.requirio_pin,
                created_at=descuento.created_at,
            )
            self.session.add(orm)
            await self.session.commit()
            await self.session.refresh(orm)
            return self._from_orm(orm)

        query = select(DescuentoORM).where(DescuentoORM.id == descuento.id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if not orm:
            raise ValueError(f"Descuento ID {descuento.id} no existe")

        orm.orden_id = descuento.orden_id
        orm.porcentaje = descuento.porcentaje
        orm.monto = descuento.monto
        orm.motivo = descuento.motivo
        orm.autorizado_por = descuento.autorizado_por
        orm.requirio_pin = descuento.requirio_pin
        await self.session.commit()
        await self.session.refresh(orm)
        return self._from_orm(orm)

    def _from_orm(self, orm: DescuentoORM) -> Descuento:
        return Descuento(
            id=orm.id,
            orden_id=orm.orden_id,
            porcentaje=orm.porcentaje,
            monto=orm.monto,
            motivo=orm.motivo,
            autorizado_por=orm.autorizado_por,
            requirio_pin=orm.requirio_pin,
            created_at=orm.created_at,
        )
