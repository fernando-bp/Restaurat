from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from app.application.services.factus_client import FactusClient
from app.config import settings


class FactusInvoiceService:
    def __init__(
        self,
        client: FactusClient | None = None,
        numbering_range_id: int | None = None,
        municipality_code: str | None = None,
    ):
        self.client = client or FactusClient()
        self._numbering_range_id = numbering_range_id or settings.factus_numbering_range_id
        self._municipality_code = municipality_code or settings.factus_customer_municipality_code

    def _normalize_invoice_response(
        self,
        response: dict[str, Any],
        *,
        fallback_reference_code: str | None = None,
        default_message: str = "Factura enviada a Factus",
    ) -> dict[str, Any]:
        data = response.get("data") if isinstance(response.get("data"), dict) else {}
        bill = data.get("bill") if isinstance(data.get("bill"), dict) else {}
        document = data.get("document") if isinstance(data.get("document"), dict) else {}
        links = data.get("links") if isinstance(data.get("links"), dict) else {}
        source = {**response, **data, **document, **bill}
        status_value = (
            source.get("status")
            or source.get("state")
            or source.get("estado")
            or response.get("message")
            or "accepted"
        )
        message = response.get("message") or response.get("detail") or default_message
        cufe = source.get("cufe") or source.get("cufe_id") or source.get("uuid")
        is_validated = source.get("is_validated")
        if is_validated is True or cufe or "validado" in message.lower() or "validada" in message.lower():
            status_value = "validated"
        elif is_validated is False:
            status_value = "processing"
        return {
            "status": str(status_value).lower(),
            "number": source.get("number") or source.get("document_number"),
            "reference_code": (
                source.get("reference_code")
                or source.get("referenceCode")
                or fallback_reference_code
            ),
            "cufe": cufe,
            "qr_url": source.get("qr_url") or source.get("qrUrl") or source.get("qr") or links.get("qr"),
            "pdf_url": (
                source.get("pdf_url")
                or source.get("pdfUrl")
                or source.get("public_url")
                or source.get("url")
                or links.get("public_url")
            ),
            "factus_response": response,
            "message": message,
        }

    def build_payload(
        self,
        *,
        order_id: int,
        order_data: dict[str, Any],
        items: list[dict[str, Any]],
        recipe_map: dict[int, dict[str, Any]],
        cliente_nombre: str | None = None,
        cliente_nit: str | None = None,
        cliente_email: str | None = None,
    ) -> dict[str, Any]:
        customer_name = (cliente_nombre or order_data.get("cliente_nombre") or "Consumidor final").strip() or "Consumidor final"
        customer_nit = (cliente_nit or order_data.get("cliente_nit") or "").strip()
        customer_email = (cliente_email or order_data.get("cliente_email") or "").strip()

        factus_items: list[dict[str, Any]] = []
        for item in items:
            recipe = recipe_map.get(int(item.get("receta_id") or 0), {})
            description = recipe.get("nombre") or f"Producto {item.get('receta_id')}"
            price = float(item.get("precio_unitario") or recipe.get("precio_venta") or 0)
            quantity = float(item.get("cantidad") or 0)
            subtotal = float(item.get("subtotal") or (price * quantity))
            taxes: list[dict[str, Any]]
            if float(order_data.get("total_iva") or 0) > 0:
                # 8% IVA — tarifa para restaurantes y servicios de alimentación en Colombia
                taxes = [{"code": "01", "rate": "08.00"}]
            else:
                taxes = [{"is_excluded": True}]

            factus_items.append({
                "code_reference": str(item.get("receta_id") or item.get("code_reference") or "item"),
                "name": description,
                "quantity": f"{quantity:.2f}",
                "discount_rate": "0.00",
                "price": f"{price:.2f}",
                "unit_measure_code": "94",
                "standard_code": "999",
                "taxes": taxes,
            })

        customer_payload: dict[str, Any] = {
            "identification_document_code": "31" if customer_nit else "13",
            "identification": customer_nit or "222222222222",
            "names": customer_name,
            "address": "N/A",
            "email": customer_email or None,
            "phone": None,
            "legal_organization_code": settings.factus_customer_legal_organization_code if customer_nit else "2",
            "tribute_code": "ZZ" if not customer_nit else "01",
            "municipality_code": self._municipality_code,
        }

        return {
            "reference_code": f"ORD-{order_id}",
            "document": settings.factus_document_type,
            "numbering_range_id": self._numbering_range_id,
            "operation_type": settings.factus_operation_type,
            "send_email": settings.factus_send_email,
            "payment_details": [
                {
                    "payment_form": settings.factus_payment_form,
                    "payment_method_code": settings.factus_payment_method_code,
                    "reference_code": f"PAY-{order_id}",
                    "amount": f"{float(order_data.get('total_neto') or 0):.2f}",
                }
            ],
            "cash_rounding_amount": "0.00",
            "observation": f"Factura generada para orden {order_id}",
            "customer": customer_payload,
            "items": factus_items,
        }

    async def emit_invoice(self, *, payload: dict[str, Any]) -> dict[str, Any]:
        if not settings.factus_enabled:
            return {
                "status": "accepted",
                "reference_code": payload.get("reference_code"),
                "cufe": None,
                "qr_url": None,
                "pdf_url": None,
                "factus_response": {"mock": True},
                "message": "Factus disabled in settings; mock accepted",
            }
        response = await self.client.post_invoice(payload)
        if isinstance(response, dict):
            return self._normalize_invoice_response(
                response,
                fallback_reference_code=payload.get("reference_code"),
            )
        return {
            "status": "accepted",
            "reference_code": payload.get("reference_code"),
            "cufe": None,
            "qr_url": None,
            "pdf_url": None,
            "factus_response": {"raw": str(response)},
            "message": "Factura enviada a Factus",
        }

    async def get_invoice_by_reference(self, reference_code: str) -> dict[str, Any]:
        response = await self.client.get_invoice_by_reference(reference_code)
        return self._normalize_invoice_response(
            response,
            fallback_reference_code=reference_code,
            default_message="Factura consultada en Factus",
        )
