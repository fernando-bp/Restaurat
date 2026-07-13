from __future__ import annotations

from pathlib import Path
from datetime import datetime
from xml.sax.saxutils import escape

from app.config import settings
from app.domain.entities.factura import Factura
from app.domain.enums.estado_factura import EstadoFacturaEnum


class DianFacturaService:
    """Servicio base para emisión de facturas electrónicas.

    En desarrollo se emite una factura simulada con XML estructurado y se deja el
    flujo listo para conectar con un proveedor o la DIAN real cuando se tengan
    credenciales y certificado digital.
    """

    async def emitir(self, factura: Factura) -> Factura:
        factura.estado = EstadoFacturaEnum.ACEPTADA
        factura.numero_documento = self._generar_numero_documento(factura)
        factura.xml_documento = self._generar_xml(factura)
        factura.url_documento = self._guardar_xml(factura)
        return factura

    def _generar_numero_documento(self, factura: Factura) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"FA-{timestamp}"

    def _generar_xml(self, factura: Factura) -> str:
        detalle_xml = "".join(
            f"<detalle><item>{escape(detalle.nombre_item)}</item><cantidad>{detalle.cantidad}</cantidad><precio>{detalle.precio_unitario}</precio><subtotal>{detalle.subtotal}</subtotal></detalle>"
            for detalle in factura.detalles
        )
        return f"""<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<FacturaElectronica>
  <numero>{factura.numero_documento or 'PENDIENTE'}</numero>
  <ordenId>{factura.orden_id}</ordenId>
  <cliente>{escape(factura.cliente_nombre or 'Consumidor final')}</cliente>
  <nit>{escape(factura.cliente_nit or 'N/A')}</nit>
  <estado>{factura.estado.value}</estado>
  <totalBruto>{factura.total_bruto}</totalBruto>
  <totalIva>{factura.total_iva}</totalIva>
  <totalNeto>{factura.total_neto}</totalNeto>
  <detalles>{detalle_xml}</detalles>
</FacturaElectronica>"""

    def _guardar_xml(self, factura: Factura) -> str:
        base_dir = Path(settings.media_root) / "facturas"
        base_dir.mkdir(parents=True, exist_ok=True)
        path = base_dir / f"{factura.numero_documento or 'factura'}.xml"
        path.write_text(factura.xml_documento or "", encoding="utf-8")
        return f"/media/facturas/{path.name}"
