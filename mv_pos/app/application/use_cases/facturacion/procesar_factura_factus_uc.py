from __future__ import annotations

import asyncio
import json
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.factus_client import FactusAPIError
from app.application.services.factus_service import FactusInvoiceService
from app.domain.entities.factura import Factura
from app.domain.enums.estado_factura import EstadoFacturaEnum
from app.infrastructure.database.models.factura import FacturaORM
from app.infrastructure.database.models.mesa import OrdenORM
from app.infrastructure.database.models.orden_item import OrdenItemORM
from app.infrastructure.database.models.receta import RecetaORM


class ProcesarFacturaFactusUC:
    def __init__(self, db: AsyncSession, service: FactusInvoiceService | None = None):
        self.db = db
        self.service = service or FactusInvoiceService()

    def _to_entity(self, factura_orm: FacturaORM) -> Factura:
        return Factura(
            id=factura_orm.id,
            orden_id=factura_orm.orden_id,
            cliente_nombre=factura_orm.cliente_nombre,
            cliente_nit=factura_orm.cliente_nit,
            cliente_email=factura_orm.cliente_email,
            numero_documento=factura_orm.numero_documento,
            estado=EstadoFacturaEnum(factura_orm.estado),
            fecha_emision=factura_orm.fecha_emision,
            total_bruto=factura_orm.total_bruto,
            total_descuento=factura_orm.total_descuento,
            total_iva=factura_orm.total_iva,
            total_neto=factura_orm.total_neto,
            xml_documento=factura_orm.xml_documento,
            url_documento=factura_orm.url_documento,
            reference_code=factura_orm.reference_code,
            cufe=factura_orm.cufe,
            qr_url=factura_orm.qr_url,
            pdf_url=factura_orm.pdf_url,
            intentos=factura_orm.intentos or 0,
            ultimo_error=factura_orm.ultimo_error,
            factus_response=factura_orm.factus_response,
        )

    def _factus_error_message(self, exc: FactusAPIError) -> str:
        if isinstance(exc.payload, dict):
            errors = exc.payload.get("data", {}).get("errors") if isinstance(exc.payload.get("data"), dict) else None
            if isinstance(errors, dict) and errors:
                return " | ".join(f"{code}: {message}" for code, message in errors.items())
            message = exc.payload.get("message")
            if message:
                return str(message)
        return str(exc)

    def _is_pending_dian_conflict(self, exc: FactusAPIError) -> bool:
        message = self._factus_error_message(exc).lower()
        return exc.status_code == 409 and "pendiente" in message and "dian" in message

    def _reference_code_for(self, factura_orm: FacturaORM, orden_id: int) -> str:
        return f"MV-{factura_orm.id}-ORD-{orden_id}"

    def _set_payload_reference(self, payload: dict, reference_code: str) -> None:
        payload["reference_code"] = reference_code
        if payload.get("payment_details"):
            payload["payment_details"][0]["reference_code"] = f"PAY-{reference_code}"

    def _apply_factus_result(self, factura_orm: FacturaORM, result: dict) -> None:
        status_value = (result.get("status") or "").lower()
        if status_value in {"accepted", "validated", "aceptada", "validada"}:
            factura_orm.estado = EstadoFacturaEnum.VALIDATED.value
        elif status_value in {"processing", "pending", "pendiente"}:
            factura_orm.estado = EstadoFacturaEnum.PROCESSING.value
        else:
            factura_orm.estado = EstadoFacturaEnum.REJECTED.value
        factura_orm.numero_documento = result.get("number") or result.get("reference_code")
        factura_orm.reference_code = result.get("reference_code")
        factura_orm.cufe = result.get("cufe")
        factura_orm.qr_url = result.get("qr_url")
        factura_orm.pdf_url = result.get("pdf_url")
        factura_orm.factus_response = result.get("factus_response") or {}
        factura_orm.ultimo_error = None if factura_orm.estado == EstadoFacturaEnum.VALIDATED.value else result.get("message")
        factura_orm.url_documento = result.get("pdf_url")
        factura_orm.updated_at = datetime.utcnow()

    async def sincronizar_con_factus(self, factura_orm: FacturaORM) -> Factura:
        reference_code = factura_orm.reference_code
        if not reference_code:
            return self._to_entity(factura_orm)
        try:
            result = await self.service.get_invoice_by_reference(reference_code)
        except FactusAPIError as exc:
            if exc.status_code == 404:
                return self._to_entity(factura_orm)
            raise
        self._apply_factus_result(factura_orm, result)
        await self.db.commit()
        return self._to_entity(factura_orm)

    async def ejecutar(self, orden_id: int, *, force: bool = False) -> Factura | None:
        orden_result = await self.db.execute(select(OrdenORM).where(OrdenORM.id == orden_id))
        orden = orden_result.scalar_one_or_none()
        if not orden:
            return None

        factura_result = await self.db.execute(select(FacturaORM).where(FacturaORM.orden_id == orden_id))
        factura_orm = factura_result.scalar_one_or_none()
        previous_estado = str(factura_orm.estado or "").lower() if factura_orm else ""
        if factura_orm and not force:
            estado_actual = str(factura_orm.estado or "").lower()
            if estado_actual in {"validated", "accepted", "aceptada", "validada"}:
                return self._to_entity(factura_orm)
            if estado_actual in {"processing", "pending", "pendiente"} and factura_orm.reference_code:
                return await self.sincronizar_con_factus(factura_orm)

        if factura_orm is None:
            factura_orm = FacturaORM(
                orden_id=orden_id,
                cliente_nombre=None,
                cliente_nit=None,
                cliente_email=None,
                estado=EstadoFacturaEnum.PENDIENTE.value,
                total_bruto=orden.total_bruto or 0,
                total_descuento=orden.total_descuento or 0,
                total_iva=orden.total_iva or 0,
                total_neto=orden.total_neto or 0,
            )
            self.db.add(factura_orm)
            await self.db.flush()

        factura_orm.estado = EstadoFacturaEnum.PENDIENTE.value
        factura_orm.intentos = (factura_orm.intentos or 0) + 1
        factura_orm.ultimo_error = None
        await self.db.flush()

        order_data = {
            "id": orden.id,
            "mesa_id": orden.mesa_id,
            "cliente_nombre": None,
            "cliente_nit": None,
            "cliente_email": None,
            "total_bruto": int(orden.total_bruto or 0),
            "total_descuento": int(orden.total_descuento or 0),
            "total_iva": int(orden.total_iva or 0),
            "total_neto": int(orden.total_neto or 0),
        }
        items_result = await self.db.execute(select(OrdenItemORM).where(OrdenItemORM.orden_id == orden_id))
        items = items_result.scalars().all()

        if not items or int(orden.total_neto or 0) <= 0:
            factura_orm.estado = EstadoFacturaEnum.REJECTED.value
            factura_orm.ultimo_error = "La orden no tiene ítems o el total es cero; no se puede facturar."
            factura_orm.updated_at = datetime.utcnow()
            await self.db.commit()
            return self._to_entity(factura_orm)

        factus_items = []
        for item in items:
            factus_items.append({
                "receta_id": item.receta_id,
                "cantidad": int(item.cantidad or 0),
                "precio_unitario": int(item.precio_unitario or 0),
                "subtotal": int((item.precio_unitario or 0) * (item.cantidad or 0)),
            })

        recipes_result = await self.db.execute(select(RecetaORM).where(RecetaORM.id.in_([item.receta_id for item in items])))
        recipe_map = {
            recipe.id: {"nombre": recipe.nombre, "precio_venta": int(recipe.precio_venta or 0)}
            for recipe in recipes_result.scalars().all()
        }

        payload = self.service.build_payload(
            order_id=orden_id,
            order_data=order_data,
            items=factus_items,
            recipe_map=recipe_map,
            cliente_nombre=factura_orm.cliente_nombre,
            cliente_nit=factura_orm.cliente_nit,
            cliente_email=factura_orm.cliente_email,
        )
        base_reference_code = self._reference_code_for(factura_orm, orden_id)
        reference_code = factura_orm.reference_code or base_reference_code
        if force:
            reference_code = f"{base_reference_code}-R{factura_orm.intentos}"
        self._set_payload_reference(payload, reference_code)
        if previous_estado in {"rejected", "rechazada"} and not factura_orm.cufe and (factura_orm.intentos or 0) > 1:
            retry_reference = f"{base_reference_code}-R{factura_orm.intentos}"
            self._set_payload_reference(payload, retry_reference)

        attempt = 0
        last_error: Exception | None = None
        max_attempts = 5
        while attempt < max_attempts:
            try:
                result = await self.service.emit_invoice(payload=payload)
                self._apply_factus_result(factura_orm, result)
                factura_orm.xml_documento = json.dumps(payload, default=str)
                await self.db.commit()
                return self._to_entity(factura_orm)
            except httpx.TimeoutException as exc:
                last_error = exc
                attempt += 1
                if attempt >= max_attempts:
                    break
                await asyncio.sleep(2 ** (attempt - 1))
                continue
            except httpx.ConnectError as exc:
                last_error = exc
                attempt += 1
                if attempt >= max_attempts:
                    break
                await asyncio.sleep(2 ** (attempt - 1))
                continue
            except FactusAPIError as exc:
                last_error = exc
                if self._is_pending_dian_conflict(exc):
                    attempt += 1
                    factura_orm.estado = EstadoFacturaEnum.PROCESSING.value
                    factura_orm.reference_code = payload.get("reference_code")
                    factura_orm.xml_documento = json.dumps(payload, default=str)
                    factura_orm.ultimo_error = self._factus_error_message(exc)
                    factura_orm.factus_response = exc.payload or {}
                    factura_orm.updated_at = datetime.utcnow()
                    await self.db.commit()
                    try:
                        return await self.sincronizar_con_factus(factura_orm)
                    except FactusAPIError:
                        pass
                    if attempt >= max_attempts:
                        return self._to_entity(factura_orm)
                    await asyncio.sleep(min(3 * attempt, 10))
                    continue

                factura_orm.estado = EstadoFacturaEnum.REJECTED.value
                factura_orm.reference_code = payload.get("reference_code")
                factura_orm.xml_documento = json.dumps(payload, default=str)
                factura_orm.ultimo_error = self._factus_error_message(exc)
                factura_orm.factus_response = exc.payload or {}
                factura_orm.updated_at = datetime.utcnow()
                await self.db.commit()
                raise
            except Exception as exc:
                factura_orm.estado = EstadoFacturaEnum.REJECTED.value
                factura_orm.ultimo_error = str(exc)
                factura_orm.updated_at = datetime.utcnow()
                await self.db.commit()
                raise

        factura_orm.estado = EstadoFacturaEnum.REJECTED.value
        factura_orm.ultimo_error = str(last_error or "No se pudo procesar la factura en Factus")
        factura_orm.updated_at = datetime.utcnow()
        await self.db.commit()
        raise RuntimeError(str(last_error or "No se pudo procesar la factura en Factus"))
