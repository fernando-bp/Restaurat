from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums.estado_factura import EstadoFacturaEnum

from app.domain.entities.factura import Factura
from app.domain.repositories.factura_repository import FacturaRepository
from app.infrastructure.database.models.factura import FacturaORM


class FacturaRepoSQLAlchemy(FacturaRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def guardar(self, factura: Factura) -> Factura:
        orm = FacturaORM(
            id=factura.id,
            orden_id=factura.orden_id,
            cliente_nombre=factura.cliente_nombre,
            cliente_nit=factura.cliente_nit,
            cliente_email=factura.cliente_email,
            numero_documento=factura.numero_documento,
            estado=factura.estado.value,
            fecha_emision=factura.fecha_emision,
            total_bruto=factura.total_bruto,
            total_descuento=factura.total_descuento,
            total_iva=factura.total_iva,
            total_neto=factura.total_neto,
            xml_documento=factura.xml_documento,
            url_documento=factura.url_documento,
            reference_code=getattr(factura, "reference_code", None),
            cufe=getattr(factura, "cufe", None),
            qr_url=getattr(factura, "qr_url", None),
            pdf_url=getattr(factura, "pdf_url", None),
            intentos=getattr(factura, "intentos", 0),
            ultimo_error=getattr(factura, "ultimo_error", None),
            factus_response=getattr(factura, "factus_response", None),
        )
        if factura.id is None:
            self.session.add(orm)
            await self.session.commit()
            await self.session.refresh(orm)
            factura.id = orm.id
            return factura

        existing = await self.session.get(FacturaORM, factura.id)
        if existing:
            existing.orden_id = factura.orden_id
            existing.cliente_nombre = factura.cliente_nombre
            existing.cliente_nit = factura.cliente_nit
            existing.cliente_email = factura.cliente_email
            existing.numero_documento = factura.numero_documento
            existing.estado = factura.estado.value
            existing.fecha_emision = factura.fecha_emision
            existing.total_bruto = factura.total_bruto
            existing.total_descuento = factura.total_descuento
            existing.total_iva = factura.total_iva
            existing.total_neto = factura.total_neto
            existing.xml_documento = factura.xml_documento
            existing.url_documento = factura.url_documento
            existing.reference_code = getattr(factura, "reference_code", None)
            existing.cufe = getattr(factura, "cufe", None)
            existing.qr_url = getattr(factura, "qr_url", None)
            existing.pdf_url = getattr(factura, "pdf_url", None)
            existing.intentos = getattr(factura, "intentos", existing.intentos or 0)
            existing.ultimo_error = getattr(factura, "ultimo_error", None)
            existing.factus_response = getattr(factura, "factus_response", None)
            await self.session.commit()
        return factura

    async def obtener_por_id(self, factura_id: int) -> Factura | None:
        orm = await self.session.get(FacturaORM, factura_id)
        if not orm:
            return None
        return Factura(
            id=orm.id,
            orden_id=orm.orden_id,
            cliente_nombre=orm.cliente_nombre,
            cliente_nit=orm.cliente_nit,
            cliente_email=orm.cliente_email,
            numero_documento=orm.numero_documento,
            estado=EstadoFacturaEnum(orm.estado) if isinstance(orm.estado, str) else orm.estado,
            fecha_emision=orm.fecha_emision,
            total_bruto=orm.total_bruto,
            total_descuento=orm.total_descuento,
            total_iva=orm.total_iva,
            total_neto=orm.total_neto,
            xml_documento=orm.xml_documento,
            url_documento=orm.url_documento,
            reference_code=orm.reference_code,
            cufe=orm.cufe,
            qr_url=orm.qr_url,
            pdf_url=orm.pdf_url,
            intentos=orm.intentos or 0,
            ultimo_error=orm.ultimo_error,
            factus_response=orm.factus_response,
        )

    async def obtener_por_orden_id(self, orden_id: int) -> list[Factura]:
        result = await self.session.execute(select(FacturaORM).where(FacturaORM.orden_id == orden_id))
        rows = result.scalars().all()
        return [
            Factura(
                id=orm.id,
                orden_id=orm.orden_id,
                cliente_nombre=orm.cliente_nombre,
                cliente_nit=orm.cliente_nit,
                cliente_email=orm.cliente_email,
                numero_documento=orm.numero_documento,
                estado=EstadoFacturaEnum(orm.estado) if isinstance(orm.estado, str) else orm.estado,
                fecha_emision=orm.fecha_emision,
                total_bruto=orm.total_bruto,
                total_descuento=orm.total_descuento,
                total_iva=orm.total_iva,
                total_neto=orm.total_neto,
                xml_documento=orm.xml_documento,
                url_documento=orm.url_documento,
                reference_code=orm.reference_code,
                cufe=orm.cufe,
                qr_url=orm.qr_url,
                pdf_url=orm.pdf_url,
                intentos=orm.intentos or 0,
                ultimo_error=orm.ultimo_error,
                factus_response=orm.factus_response,
            )
            for orm in rows
        ]
