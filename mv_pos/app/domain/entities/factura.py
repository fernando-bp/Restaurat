from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List

from app.domain.enums.estado_factura import EstadoFacturaEnum


@dataclass
class FacturaDetalle:
    id: int | None = None
    receta_id: int | None = None
    nombre_item: str = ""
    cantidad: int = 1
    precio_unitario: int = 0
    subtotal: int = 0


@dataclass
class Factura:
    id: int | None
    orden_id: int
    cliente_nombre: str | None = None
    cliente_nit: str | None = None
    cliente_email: str | None = None
    numero_documento: str | None = None
    estado: EstadoFacturaEnum = EstadoFacturaEnum.BORRADOR
    fecha_emision: datetime = field(default_factory=datetime.utcnow)
    total_bruto: int = 0
    total_descuento: int = 0
    total_iva: int = 0
    total_neto: int = 0
    xml_documento: str | None = None
    url_documento: str | None = None
    reference_code: str | None = None
    cufe: str | None = None
    qr_url: str | None = None
    pdf_url: str | None = None
    intentos: int = 0
    ultimo_error: str | None = None
    factus_response: dict | None = None
    detalles: List[FacturaDetalle] = field(default_factory=list)
