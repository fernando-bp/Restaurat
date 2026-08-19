"""
RF-29: Registrar pagos con tarjeta (débito/crédito) con referencia de datafono
RF-30: Registrar pagos por transferencia (Nequi, Daviplata, PSE) con comprobante
"""
import asyncio
import logging
from decimal import Decimal
from datetime import datetime

from app.domain.entities.pago import Pago
from app.domain.enums.forma_pago import FormaPagoEnum
from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.repositories.orden_repository import OrdenRepository
from app.domain.repositories.pago_repository import PagoRepository
from app.domain.repositories.mesa_repository import MesaRepository
from app.infrastructure.database.connection import async_session
from app.application.use_cases.facturacion.procesar_factura_factus_uc import ProcesarFacturaFactusUC

logger = logging.getLogger(__name__)


class RegistrarPagoTarjetaUseCase:
    """Registra pagos con tarjeta (RF-29)"""

    def __init__(
        self,
        orden_repo: OrdenRepository,
        pago_repo: PagoRepository,
        mesa_repo: MesaRepository,
    ):
        self.orden_repo = orden_repo
        self.pago_repo = pago_repo
        self.mesa_repo = mesa_repo

    async def ejecutar(
        self,
        orden_id: int,
        monto: Decimal,
        tipo_tarjeta: str,
        referencia_datafono: str,
        cajero_id: int,
    ) -> dict:
        if tipo_tarjeta not in ('debito', 'credito'):
            raise ValueError("tipo_tarjeta debe ser 'debito' o 'credito'")

        if not referencia_datafono or len(referencia_datafono.strip()) == 0:
            raise ValueError("referencia_datafono es obligatoria para pagos con tarjeta (RF-29)")

        orden = await self.orden_repo.obtener_por_id(orden_id)
        if not orden:
            raise ValueError(f"Orden {orden_id} no encontrada")
        if orden.estado == EstadoOrdenEnum.CANCELADA:
            raise ValueError("No se puede pagar una orden cancelada")
        if orden.estado == EstadoOrdenEnum.PAGADA:
            raise ValueError("La orden ya fue pagada")

        forma_pago = (
            FormaPagoEnum.TARJETA_DEBITO if tipo_tarjeta == 'debito'
            else FormaPagoEnum.TARJETA_CREDITO
        )

        pago = Pago(
            id=None,
            orden_id=orden_id,
            forma_pago=forma_pago,
            monto=monto,
            referencia_datafono=referencia_datafono,
            cajero_id=cajero_id,
            created_at=datetime.utcnow(),
        )
        pago.validar_tarjeta()

        pago_guardado = await self.pago_repo.guardar(pago)

        pagos_anteriores = await self.pago_repo.listar_por_orden(orden_id)
        total_pagado = sum(p.monto for p in pagos_anteriores)
        if total_pagado >= Decimal(orden.total_neto):
            orden.estado = EstadoOrdenEnum.PAGADA
            orden.hora_cierre = datetime.utcnow()
            await self.orden_repo.guardar(orden)

            async def _disparar_facturacion() -> None:
                async with async_session() as session:
                    try:
                        await ProcesarFacturaFactusUC(session).ejecutar(orden_id)
                    except Exception as exc:
                        logger.error("Error generando factura para orden %s: %s", orden_id, exc)

            asyncio.create_task(_disparar_facturacion())

            mesa = await self.mesa_repo.obtener_por_id(orden.mesa_id)
            if mesa:
                mesa.estado = 'libre'
                await self.mesa_repo.guardar(mesa)

        return {
            'pago_id': pago_guardado.id,
            'monto': pago_guardado.monto,
            'tipo_tarjeta': tipo_tarjeta,
            'referencia_datafono': referencia_datafono,
            'exito': True,
        }


class RegistrarPagoTransferenciaUseCase:
    """Registra pagos por transferencia (RF-30)"""

    def __init__(
        self,
        orden_repo: OrdenRepository,
        pago_repo: PagoRepository,
        mesa_repo: MesaRepository,
    ):
        self.orden_repo = orden_repo
        self.pago_repo = pago_repo
        self.mesa_repo = mesa_repo

    async def ejecutar(
        self,
        orden_id: int,
        monto: Decimal,
        tipo_transferencia: str,
        numero_comprobante: str,
        cajero_id: int,
    ) -> dict:
        if tipo_transferencia not in ('nequi', 'daviplata', 'pse'):
            raise ValueError("tipo_transferencia debe ser 'nequi', 'daviplata' o 'pse'")

        if not numero_comprobante or len(numero_comprobante.strip()) == 0:
            raise ValueError("numero_comprobante es obligatorio para transferencias (RF-30)")

        orden = await self.orden_repo.obtener_por_id(orden_id)
        if not orden:
            raise ValueError(f"Orden {orden_id} no encontrada")
        if orden.estado == EstadoOrdenEnum.CANCELADA:
            raise ValueError("No se puede pagar una orden cancelada")
        if orden.estado == EstadoOrdenEnum.PAGADA:
            raise ValueError("La orden ya fue pagada")

        forma_pago_map = {
            'nequi': FormaPagoEnum.NEQUI,
            'daviplata': FormaPagoEnum.DAVIPLATA,
            'pse': FormaPagoEnum.PSE,
        }

        pago = Pago(
            id=None,
            orden_id=orden_id,
            forma_pago=forma_pago_map[tipo_transferencia],
            monto=monto,
            numero_comprobante=numero_comprobante,
            cajero_id=cajero_id,
            created_at=datetime.utcnow(),
        )
        pago.validar_transferencia()

        pago_guardado = await self.pago_repo.guardar(pago)

        pagos_anteriores = await self.pago_repo.listar_por_orden(orden_id)
        total_pagado = sum(p.monto for p in pagos_anteriores)
        if total_pagado >= Decimal(orden.total_neto):
            orden.estado = EstadoOrdenEnum.PAGADA
            orden.hora_cierre = datetime.utcnow()
            await self.orden_repo.guardar(orden)

            async def _disparar_facturacion() -> None:
                async with async_session() as session:
                    try:
                        await ProcesarFacturaFactusUC(session).ejecutar(orden_id)
                    except Exception as exc:
                        logger.error("Error generando factura para orden %s: %s", orden_id, exc)

            asyncio.create_task(_disparar_facturacion())

            mesa = await self.mesa_repo.obtener_por_id(orden.mesa_id)
            if mesa:
                mesa.estado = 'libre'
                await self.mesa_repo.guardar(mesa)

        return {
            'pago_id': pago_guardado.id,
            'monto': pago_guardado.monto,
            'tipo_transferencia': tipo_transferencia,
            'numero_comprobante': numero_comprobante,
            'exito': True,
        }
