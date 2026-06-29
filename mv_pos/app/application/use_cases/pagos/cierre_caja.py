from __future__ import annotations
from datetime import datetime
from decimal import Decimal

from sqlalchemy import cast, Date, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.cierre_caja import CierreCaja
from app.infrastructure.database.models.mesa import OrdenORM
from app.infrastructure.database.models.pago import PagoORM
from app.infrastructure.database.models.pago import CierreCajaORM


class RegistrarCierreCajaUC:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ejecutar(
        self,
        fecha: str,
        total_efectivo_contado: Decimal,
        observaciones: str | None,
        cajero_id: int,
    ) -> CierreCaja:
        # Obtener órdenes pagadas en la fecha indicada
        query_ordenes = select(OrdenORM).where(
            OrdenORM.estado == 'pagada',
            cast(OrdenORM.hora_cierre, Date) == fecha,
        )
        result = await self.db.execute(query_ordenes)
        ordenes = result.scalars().all()

        total_ventas = Decimal(0)
        total_descuentos = Decimal(0)
        for orden in ordenes:
            total_ventas += Decimal(orden.total_neto or 0)
            total_descuentos += Decimal(orden.total_descuento or 0)

        query_pagos = select(PagoORM).join(OrdenORM, PagoORM.orden_id == OrdenORM.id).where(
            OrdenORM.estado == 'pagada',
            cast(OrdenORM.hora_cierre, Date) == fecha,
        )
        result = await self.db.execute(query_pagos)
        pagos = result.scalars().all()

        total_efectivo_sistema = Decimal(0)
        total_tarjeta = Decimal(0)
        total_transferencia = Decimal(0)
        total_cortesia = Decimal(0)

        for pago in pagos:
            if pago.forma_pago == 'efectivo':
                total_efectivo_sistema += Decimal(pago.monto or 0)
            elif pago.forma_pago in ('tarjeta_debito', 'tarjeta_credito'):
                total_tarjeta += Decimal(pago.monto or 0)
            elif pago.forma_pago in ('nequi', 'daviplata', 'pse', 'qr_breb'):
                total_transferencia += Decimal(pago.monto or 0)
            elif pago.forma_pago == 'cortesia':
                total_cortesia += Decimal(pago.monto or 0)

        cierre = CierreCaja(
            id=None,
            fecha=fecha,
            cajero_id=cajero_id,
            total_ventas=total_ventas.quantize(Decimal('1')),
            total_efectivo_sistema=total_efectivo_sistema.quantize(Decimal('1')),
            total_efectivo_contado=total_efectivo_contado.quantize(Decimal('1')),
            total_tarjeta=total_tarjeta.quantize(Decimal('1')),
            total_transferencia=total_transferencia.quantize(Decimal('1')),
            total_cortesia=total_cortesia.quantize(Decimal('1')),
            total_descuentos=total_descuentos.quantize(Decimal('1')),
            observaciones=observaciones,
            firmado_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )

        cierre_guardado = CierreCajaORM(
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
        self.db.add(cierre_guardado)
        await self.db.commit()
        await self.db.refresh(cierre_guardado)

        return CierreCaja(
            id=cierre_guardado.id,
            fecha=str(cierre_guardado.fecha),
            cajero_id=cierre_guardado.cajero_id,
            autorizado_por=cierre_guardado.autorizado_por,
            total_ventas=cierre_guardado.total_ventas,
            total_efectivo_sistema=cierre_guardado.total_efectivo_sistema,
            total_efectivo_contado=cierre_guardado.total_efectivo_contado,
            total_tarjeta=cierre_guardado.total_tarjeta,
            total_transferencia=cierre_guardado.total_transferencia,
            total_cortesia=cierre_guardado.total_cortesia,
            total_descuentos=cierre_guardado.total_descuentos,
            observaciones=cierre_guardado.observaciones,
            firmado_at=cierre_guardado.firmado_at,
            created_at=cierre_guardado.created_at,
        )
