from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.bold_qr_test.client import BoldQrTestClient
from app.integrations.bold_qr_test.models import BoldQrPagoIndependienteORM
from app.integrations.bold_qr_test.repository import BoldQrTestRepository


APPROVED_EVENTS = {"SALE_APPROVED", "PAYMENT_APPROVED", "APPROVED"}
REJECTED_EVENTS = {"SALE_REJECTED", "PAYMENT_REJECTED", "REJECTED", "DECLINED"}
VOID_EVENTS = {"VOID_APPROVED", "VOID_REJECTED"}


class BoldQrTestService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BoldQrTestRepository(session)
        self.client = BoldQrTestClient(settings.bold_api_base_url, settings.bold_api_key)

    async def create_payment(self, *, monto: Decimal, cajero_id: int | None, descripcion: str | None) -> BoldQrPagoIndependienteORM:
        amount = monto.quantize(Decimal("1"))
        if amount <= 0:
            raise ValueError("El monto debe ser mayor a cero")

        reference = self._build_reference()
        await self.client.create_payment_intent(
            amount=amount,
            reference=reference,
            description=descripcion or "Pago Bold prueba POS",
        )
        bold_response = await self.client.create_qr_payment(reference=reference)

        payment = BoldQrPagoIndependienteORM(
            orden_id=None,
            mesa_id=None,
            cajero_id=cajero_id,
            monto=amount,
            moneda="COP",
            referencia=self._extract_reference(bold_response, reference),
            bold_payment_id=self._extract_payment_id(bold_response),
            estado=self._normalize_status(bold_response.get("status")),
            metodo_pago="QR_BREB",
            qr_payload=self._extract_qr_payload(bold_response),
            qr_url=self._extract_qr_url(bold_response),
            expires_at=self._parse_datetime(self._extract_expires_at(bold_response))
            or datetime.utcnow() + timedelta(minutes=settings.bold_qr_expiration_minutes),
            confirmado_en_pos=0,
        )
        return await self.repo.add(payment)

    async def get_payment(self, payment_id: int) -> BoldQrPagoIndependienteORM | None:
        payment = await self.repo.get_by_id(payment_id)
        if payment and payment.estado == "PENDIENTE" and payment.expires_at and payment.expires_at < datetime.utcnow():
            payment.estado = "EXPIRADO"
            payment = await self.repo.save(payment)
        return payment

    async def process_webhook_fast(self, event: dict[str, Any]) -> tuple[BoldQrPagoIndependienteORM | None, str]:
        webhook_id = event.get("id")
        if webhook_id:
            existing = await self.repo.get_by_webhook_id(str(webhook_id))
            if existing:
                return existing, "duplicate"

        data = event.get("data") or {}
        reference = self._extract_event_reference(data)
        payment_id = data.get("payment_id") or event.get("subject")

        payment = None
        if reference:
            payment = await self.repo.get_by_reference(str(reference))
        if payment is None and payment_id:
            payment = await self.repo.get_by_bold_payment_id(str(payment_id))
        if payment is None:
            return None, "not_found"

        if payment.estado == "APROBADO":
            return payment, "already_approved"

        event_type = str(event.get("type") or "").upper()
        try:
            self._validate_amount(payment, data)
            payment.bold_payment_id = str(payment_id) if payment_id else payment.bold_payment_id
            payment.webhook_id = str(webhook_id) if webhook_id else payment.webhook_id
            payment.webhook_evento = event

            if event_type in APPROVED_EVENTS:
                payment.estado = "APROBADO"
                payment.approved_at = datetime.utcnow()
            elif event_type in REJECTED_EVENTS:
                payment.estado = "RECHAZADO"
            elif event_type in VOID_EVENTS:
                payment.estado = "RECHAZADO" if event_type == "VOID_APPROVED" else "ERROR"
            else:
                payment.estado = payment.estado or "PENDIENTE"

            await self.repo.save(payment)
            return payment, payment.estado.lower()
        except ValueError as exc:
            payment.estado = "ERROR"
            payment.ultimo_error = str(exc)
            payment.webhook_id = str(webhook_id) if webhook_id else payment.webhook_id
            payment.webhook_evento = event
            await self.repo.save(payment)
            return payment, "error"

    def _validate_amount(self, payment: BoldQrPagoIndependienteORM, data: dict[str, Any]) -> None:
        amount_data = data.get("amount") or {}
        amount = amount_data.get("total") or amount_data.get("total_amount")
        currency = amount_data.get("currency") or payment.moneda

        if currency != payment.moneda:
            raise ValueError("La moneda del webhook no coincide")
        if amount is not None and Decimal(str(amount)).quantize(Decimal("1")) != Decimal(payment.monto):
            raise ValueError("El monto del webhook no coincide")

    def _build_reference(self) -> str:
        return f"BOLD-TEST-{datetime.utcnow():%Y%m%d%H%M%S}-{uuid4().hex[:8].upper()}"

    def _normalize_status(self, status: Any) -> str:
        value = str(status or "PENDING").upper()
        if value in {"APPROVED", "SALE_APPROVED", "PAYMENT_APPROVED", "APROBADO"}:
            return "APROBADO"
        if value in {"REJECTED", "DECLINED", "FAILED", "SALE_REJECTED", "RECHAZADO"}:
            return "RECHAZADO"
        if value in {"EXPIRED", "EXPIRADO"}:
            return "EXPIRADO"
        return "PENDIENTE"

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)

    def _extract_payment_id(self, response: dict[str, Any]) -> str | None:
        return (
            response.get("transaction_id")
            or response.get("payment_intent_id")
            or response.get("payment_id")
            or response.get("id")
        )

    def _extract_reference(self, response: dict[str, Any], fallback: str) -> str:
        metadata = response.get("metadata") or {}
        return response.get("reference_id") or response.get("reference") or metadata.get("reference") or fallback

    def _extract_qr_payload(self, response: dict[str, Any]) -> str | None:
        qr = response.get("qr") or {}
        next_actions = response.get("next_actions") or {}
        return (
            next_actions.get("qr_payload")
            or response.get("qr_payload")
            or response.get("qr_code")
            or qr.get("payload")
            or qr.get("code")
        )

    def _extract_qr_url(self, response: dict[str, Any]) -> str | None:
        qr = response.get("qr") or {}
        next_actions = response.get("next_actions") or {}
        return (
            next_actions.get("qr_url")
            or response.get("qr_url")
            or response.get("qr_image_url")
            or qr.get("url")
            or qr.get("image_url")
        )

    def _extract_expires_at(self, response: dict[str, Any]) -> str | None:
        next_actions = response.get("next_actions") or {}
        return next_actions.get("expires_at") or response.get("expires_at")

    def _extract_event_reference(self, data: dict[str, Any]) -> str | None:
        metadata = data.get("metadata") or {}
        return (
            metadata.get("reference")
            or metadata.get("order_id")
            or data.get("reference")
            or data.get("order_id")
            or data.get("bold_order_id")
            or data.get("bold-order-id")
        )
