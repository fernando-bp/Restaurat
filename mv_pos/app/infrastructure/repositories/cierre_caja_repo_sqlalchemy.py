from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.cierre_caja_repository import CierreCajaRepository
from app.domain.entities.cierre_caja import CierreCaja
from app.infrastructure.database.models.pago import CierreCajaORM


class CierreCajaRepoSQLAlchemy(CierreCajaRepository):
    def __init__(self, session: AsyncSession, restaurante_id: int = 1):
        self.session = session
        self.restaurante_id = restaurante_id

    async def obtener_por_fecha(self, fecha: str) -> CierreCaja | None:
        query = select(CierreCajaORM).where(
            CierreCajaORM.fecha == fecha,
            CierreCajaORM.restaurante_id == self.restaurante_id,
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return self._from_orm(orm) if orm else None

    async def guardar(self, cierre: CierreCaja) -> CierreCaja:
        if cierre.id is None:
            orm = CierreCajaORM(
                restaurante_id=self.restaurante_id,
                fecha=cierre.fecha,
                cajero_id=cierre.cajero_id,
                autorizado_por=cierre.autorizado_por,
                total_ventas=cierre.total_ventas,
                total_efectivo_sistema=cierre.total_efectivo_sistema,
                total_efectivo_contado=cierre.total_efectivo_contado,
                total_tarjeta=cierre.total_tarjeta,
                total_transferencia=cierre.total_transferencia,
                total_cortesia=cierre.total_cortesia,
                total_descuentos=cierre.total_descuentos,
                observaciones=cierre.observaciones,
                firmado_at=cierre.firmado_at,
                created_at=cierre.created_at,
            )
            self.session.add(orm)
            await self.session.commit()
            await self.session.refresh(orm)
            return self._from_orm(orm)

        query = select(CierreCajaORM).where(
            CierreCajaORM.id == cierre.id,
            CierreCajaORM.restaurante_id == self.restaurante_id,
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if not orm:
            raise ValueError(f"Cierre de caja ID {cierre.id} no existe")

        orm.cajero_id = cierre.cajero_id
        orm.autorizado_por = cierre.autorizado_por
        orm.total_ventas = cierre.total_ventas
        orm.total_efectivo_sistema = cierre.total_efectivo_sistema
        orm.total_efectivo_contado = cierre.total_efectivo_contado
        orm.total_tarjeta = cierre.total_tarjeta
        orm.total_transferencia = cierre.total_transferencia
        orm.total_cortesia = cierre.total_cortesia
        orm.total_descuentos = cierre.total_descuentos
        orm.observaciones = cierre.observaciones
        orm.firmado_at = cierre.firmado_at
        await self.session.commit()
        await self.session.refresh(orm)
        return self._from_orm(orm)

    def _from_orm(self, orm: CierreCajaORM) -> CierreCaja:
        return CierreCaja(
            id=orm.id,
            fecha=str(orm.fecha),
            cajero_id=orm.cajero_id,
            autorizado_por=orm.autorizado_por,
            total_ventas=orm.total_ventas,
            total_efectivo_sistema=orm.total_efectivo_sistema,
            total_efectivo_contado=orm.total_efectivo_contado,
            total_tarjeta=orm.total_tarjeta,
            total_transferencia=orm.total_transferencia,
            total_cortesia=orm.total_cortesia,
            total_descuentos=orm.total_descuentos,
            observaciones=orm.observaciones,
            firmado_at=orm.firmado_at,
            created_at=orm.created_at,
        )
