from __future__ import annotations

from app.application.services.facturacion_service import DianFacturaService
from app.domain.entities.factura import Factura, FacturaDetalle
from app.domain.repositories.factura_repository import FacturaRepository
from app.domain.repositories.orden_repository import OrdenRepository


class EmitirFacturaUseCase:
    def __init__(
        self,
        orden_repo: OrdenRepository,
        factura_repo: FacturaRepository,
        dian_service: DianFacturaService | None = None,
    ):
        self.orden_repo = orden_repo
        self.factura_repo = factura_repo
        self.dian_service = dian_service or DianFacturaService()

    async def execute(
        self,
        orden_id: int,
        cliente_nombre: str | None = None,
        cliente_nit: str | None = None,
        cliente_email: str | None = None,
    ) -> Factura:
        orden = await self.orden_repo.obtener_por_id(orden_id)
        if not orden:
            raise ValueError(f"No existe la orden {orden_id}")

        facturas_existentes = await self.factura_repo.obtener_por_orden_id(orden_id)
        if facturas_existentes:
            return facturas_existentes[0]

        detalles = [
            FacturaDetalle(
                receta_id=item.receta_id,
                nombre_item=f"Item {item.receta_id}",
                cantidad=item.cantidad,
                precio_unitario=item.precio_unitario,
                subtotal=item.subtotal(),
            )
            for item in orden.items
        ]

        factura = Factura(
            id=None,
            orden_id=orden.id,
            cliente_nombre=cliente_nombre,
            cliente_nit=cliente_nit,
            cliente_email=cliente_email,
            total_bruto=orden.total_bruto,
            total_descuento=orden.total_descuento,
            total_iva=orden.total_iva,
            total_neto=orden.total_neto,
            detalles=detalles,
        )

        factura_guardada = await self.factura_repo.guardar(factura)
        factura_emitida = await self.dian_service.emitir(factura_guardada)
        return await self.factura_repo.guardar(factura_emitida)
