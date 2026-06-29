from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from typing import List

from app.domain.enums.forma_pago import FormaPagoEnum
from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.entities.pago import Pago
from app.domain.repositories.orden_repository import OrdenRepository
from app.domain.repositories.pago_repository import PagoRepository
from app.domain.repositories.mesa_repository import MesaRepository


class RegistrarPagoMixtoUC:
    def __init__(
        self,
        orden_repo: OrdenRepository,
        pago_repo: PagoRepository,
        mesa_repo: MesaRepository,
    ):
        self.orden_repo = orden_repo
        self.pago_repo = pago_repo
        self.mesa_repo = mesa_repo

    async def ejecutar(self, orden_id: int, pagos: List[dict], cajero_id: int) -> list[dict]:
        orden = await self.orden_repo.obtener_por_id(orden_id)
        if not orden:
            raise ValueError(f"Orden {orden_id} no encontrada")
        if orden.estado == EstadoOrdenEnum.CANCELADA:
            raise ValueError("No se puede pagar una orden cancelada")

        existentes = await self.pago_repo.listar_por_orden(orden_id)
        total_pagado_anterior = sum(p.monto for p in existentes)
        total_adeudado = Decimal(orden.total_neto) - total_pagado_anterior

        total_nuevo = sum(Decimal(str(item['monto'])) for item in pagos)
        if total_nuevo != total_adeudado:
            raise ValueError(
                f"La suma de pagos mixtos debe ser igual al total adeudado: {total_adeudado}. "
                f"Suma proporcionada: {total_nuevo}"
            )

        responses = []
        for pago_data in pagos:
            forma_pago = FormaPagoEnum(pago_data['forma_pago'])
            monto = Decimal(str(pago_data['monto']))
            monto_recibido = Decimal(str(pago_data['monto_recibido'])) if pago_data.get('monto_recibido') is not None else None
            referencia = pago_data.get('referencia_datafono')
            comprobante = pago_data.get('numero_comprobante')

            pago = Pago(
                id=None,
                orden_id=orden_id,
                forma_pago=forma_pago,
                monto=monto,
                monto_recibido=monto_recibido,
                referencia_datafono=referencia,
                numero_comprobante=comprobante,
                cajero_id=cajero_id,
                created_at=datetime.utcnow(),
            )
            pago.validar()
            if forma_pago == FormaPagoEnum.EFECTIVO:
                pago.cambio_entregado = pago.calcular_cambio()
            pago_guardado = await self.pago_repo.guardar(pago)
            responses.append({
                'pago_id': pago_guardado.id,
                'forma_pago': pago_guardado.forma_pago.value,
                'monto': pago_guardado.monto,
            })

        if total_adeudado == total_nuevo:
            orden.estado = EstadoOrdenEnum.PAGADA
            orden.hora_cierre = datetime.utcnow()
            await self.orden_repo.guardar(orden)

            try:
                mesa = await self.mesa_repo.obtener_por_id(orden.mesa_id)
                if mesa:
                    mesa.estado = 'libre'
                    await self.mesa_repo.guardar(mesa)
            except Exception:
                pass

        return responses
