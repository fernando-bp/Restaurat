from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.pago_repository import PagoRepository
from app.domain.entities.pago import Pago
from app.domain.enums.forma_pago import FormaPagoEnum
from app.infrastructure.database.models.pago import PagoORM


class PagoRepoSQLAlchemy(PagoRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def obtener_por_id(self, pago_id: int) -> Pago | None:
        query = select(PagoORM).where(PagoORM.id == pago_id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if orm is None:
            return None
        return self._from_orm(orm)

    async def listar_por_orden(self, orden_id: int) -> list[Pago]:
        query = select(PagoORM).where(PagoORM.orden_id == orden_id)
        result = await self.session.execute(query)
        rows = result.scalars().all()
        return [self._from_orm(row) for row in rows]

    async def guardar(self, pago: Pago) -> Pago:
        if pago.id is None:
            orm = PagoORM(
                orden_id=pago.orden_id,
                forma_pago=pago.forma_pago.value,
                monto=pago.monto,
                monto_recibido=pago.monto_recibido,
                cambio_entregado=pago.cambio_entregado,
                referencia_datafono=pago.referencia_datafono,
                numero_comprobante=pago.numero_comprobante,
                cajero_id=pago.cajero_id,
                created_at=pago.created_at,
            )
            self.session.add(orm)
            await self.session.commit()
            await self.session.refresh(orm)
            return self._from_orm(orm)

        query = select(PagoORM).where(PagoORM.id == pago.id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if not orm:
            raise ValueError(f"Pago ID {pago.id} no existe")

        orm.orden_id = pago.orden_id
        orm.forma_pago = pago.forma_pago.value
        orm.monto = pago.monto
        orm.monto_recibido = pago.monto_recibido
        orm.cambio_entregado = pago.cambio_entregado
        orm.referencia_datafono = pago.referencia_datafono
        orm.numero_comprobante = pago.numero_comprobante
        orm.cajero_id = pago.cajero_id
        await self.session.commit()
        await self.session.refresh(orm)
        return self._from_orm(orm)

    def _from_orm(self, orm: PagoORM) -> Pago:
        return Pago(
            id=orm.id,
            orden_id=orm.orden_id,
            forma_pago=FormaPagoEnum(orm.forma_pago),
            monto=orm.monto,
            monto_recibido=orm.monto_recibido,
            cambio_entregado=orm.cambio_entregado,
            referencia_datafono=orm.referencia_datafono,
            numero_comprobante=orm.numero_comprobante,
            cajero_id=orm.cajero_id,
            created_at=orm.created_at,
        )
