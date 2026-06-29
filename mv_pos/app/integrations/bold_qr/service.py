from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.entities.pago import Pago
from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.enums.forma_pago import FormaPagoEnum
from app.infrastructure.repositories.mesa_repo_sqlalchemy import MesaRepoSQLAlchemy
from app.infrastructure.repositories.orden_repo_sqlalchemy import OrdenRepoSQLAlchemy
from app.infrastructure.repositories.pago_repo_sqlalchemy import PagoRepoSQLAlchemy
from app.integrations.bold_qr.client import BoldClient, BoldClientError
from app.integrations.bold_qr.models import BoldPaymentIntentORM
from app.integrations.bold_qr.repository import BoldQrRepository
from app.integrations.bold_qr_test.models import BoldQrPagoIndependienteORM
from app.integrations.bold_qr_test.repository import BoldQrTestRepository


APPROVED_EVENTS = {"SALE_APPROVED", "PAYMENT_APPROVED", "APPROVED"}
REJECTED_EVENTS = {"SALE_REJECTED", "PAYMENT_REJECTED", "REJECTED", "DECLINED"}
CHECKOUT_SCRIPT_URL = "https://checkout.bold.co/library/boldPaymentButton.js"
ORDER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,60}$")
URL_PATTERN = re.compile(r"https?://", re.IGNORECASE)


class BoldQrService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = BoldQrRepository(session)
        self.orden_repo = OrdenRepoSQLAlchemy(session)
        self.pago_repo = PagoRepoSQLAlchemy(session)
        self.mesa_repo = MesaRepoSQLAlchemy(session)
        self.client = BoldClient(settings.bold_api_base_url, settings.bold_api_key)

    async def create_intent(
        self,
        *,
        orden_id: int,
        mesa_id: int | None,
        monto: Decimal | None,
        cajero_id: int | None,
        payer_name: str | None,
    ) -> BoldPaymentIntentORM:
        orden = await self.orden_repo.obtener_por_id(orden_id)
        if not orden:
            raise ValueError(f"Orden {orden_id} no encontrada")
        if orden.estado in (EstadoOrdenEnum.PAGADA, EstadoOrdenEnum.CANCELADA):
            raise ValueError("La orden no está disponible para pago")

        pagos = await self.pago_repo.listar_por_orden(orden_id)
        total_pagado = sum(Decimal(p.monto or 0) for p in pagos)
        saldo = Decimal(orden.total_neto or 0) - total_pagado
        amount = (monto or saldo).quantize(Decimal("1"))
        if amount <= 0:
            raise ValueError("La orden no tiene saldo pendiente")
        if amount > saldo:
            raise ValueError("El monto supera el saldo pendiente de la orden")

        effective_mesa_id = mesa_id or orden.mesa_id
        reference = self._build_reference(orden_id, effective_mesa_id)
        bold_response = await self.client.create_qr_breb_intent(
            amount=amount,
            reference=reference,
            payer_name=payer_name or f"Cliente Mesa {effective_mesa_id}",
        )

        intent = BoldPaymentIntentORM(
            orden_id=orden_id,
            mesa_id=effective_mesa_id,
            cajero_id=cajero_id,
            monto=amount,
            moneda="COP",
            referencia=bold_response.get("reference") or reference,
            bold_payment_id=bold_response.get("payment_intent_id") or bold_response.get("id"),
            estado=self._normalize_status(bold_response.get("status")),
            metodo_pago="QR_BREB",
            qr_payload=bold_response.get("qr_payload"),
            expires_at=self._parse_datetime(bold_response.get("expires_at"))
            or datetime.utcnow() + timedelta(minutes=settings.bold_qr_expiration_minutes),
        )
        return await self.repo.add(intent)

    async def get_intent(self, intent_id: int) -> BoldPaymentIntentORM | None:
        intent = await self.repo.get_by_id(intent_id)
        if intent and intent.estado == "PENDIENTE" and intent.expires_at and intent.expires_at < datetime.utcnow():
            intent.estado = "EXPIRADO"
            intent = await self.repo.save(intent)
        return intent

    async def process_webhook(self, event: dict[str, Any]) -> tuple[BoldPaymentIntentORM | None, str]:
        webhook_id = event.get("id")
        if webhook_id:
            existing = await self.repo.get_by_webhook_id(webhook_id)
            if existing:
                return existing, "duplicate"

        data = event.get("data") or {}
        payment_id = data.get("payment_id") or data.get("payment_intent_id") or data.get("id")
        reference = ((data.get("metadata") or {}).get("reference") or data.get("reference"))

        intent = None
        if reference:
            intent = await self.repo.get_by_reference(reference)
        if intent is None and payment_id:
            intent = await self.repo.get_by_bold_payment_id(payment_id)
        if intent is None:
            return None, "not_found"

        event_type = (event.get("type") or "").upper()
        if event_type in REJECTED_EVENTS:
            intent.estado = "RECHAZADO"
            intent.webhook_id = webhook_id
            await self.repo.save(intent)
            return intent, "rejected"

        if event_type not in APPROVED_EVENTS:
            return intent, "ignored"

        self._validate_webhook_amount(intent, data)
        confirmed = await self._confirm_with_bold(intent)
        if not confirmed:
            intent.ultimo_error = "Bold no confirmó el pago como aprobado"
            await self.repo.save(intent)
            return intent, "not_confirmed"

        await self._register_pos_payment(intent, webhook_id)
        return intent, "approved"

    async def _register_pos_payment(self, intent: BoldPaymentIntentORM, webhook_id: str | None) -> None:
        if intent.estado == "APROBADO":
            return

        pago = Pago(
            id=None,
            orden_id=intent.orden_id,
            forma_pago=FormaPagoEnum.QR_BREB,
            monto=Decimal(intent.monto),
            numero_comprobante=intent.bold_payment_id or intent.referencia,
            cajero_id=intent.cajero_id,
            created_at=datetime.utcnow(),
        )
        pago.validar_transferencia()
        await self.pago_repo.guardar(pago)

        orden = await self.orden_repo.obtener_por_id(intent.orden_id)
        if orden:
            pagos = await self.pago_repo.listar_por_orden(intent.orden_id)
            total_pagado = sum(Decimal(p.monto or 0) for p in pagos)
            if total_pagado >= Decimal(orden.total_neto or 0):
                orden.estado = EstadoOrdenEnum.PAGADA
                orden.hora_cierre = datetime.utcnow()
                await self.orden_repo.guardar(orden)

                mesa = await self.mesa_repo.obtener_por_id(orden.mesa_id)
                if mesa:
                    mesa.estado = "libre"
                    await self.mesa_repo.guardar(mesa)

        intent.estado = "APROBADO"
        intent.webhook_id = webhook_id
        await self.repo.save(intent)

    async def _confirm_with_bold(self, intent: BoldPaymentIntentORM) -> bool:
        if not intent.bold_payment_id:
            return True
        try:
            response = await self.client.get_payment_intent(intent.bold_payment_id)
        except BoldClientError:
            return False
        status = self._normalize_status(response.get("status"))
        return status == "APROBADO"

    def _validate_webhook_amount(self, intent: BoldPaymentIntentORM, data: dict[str, Any]) -> None:
        amount_data = data.get("amount") or {}
        amount = amount_data.get("total") or amount_data.get("total_amount")
        currency = amount_data.get("currency") or intent.moneda
        if currency != intent.moneda:
            raise ValueError("La moneda del webhook no coincide")
        if amount is not None and Decimal(str(amount)).quantize(Decimal("1")) != Decimal(intent.monto):
            raise ValueError("El monto del webhook no coincide")

    def _build_reference(self, orden_id: int, mesa_id: int | None) -> str:
        suffix = uuid4().hex[:6].upper()
        return f"ORD-{orden_id}-MESA-{mesa_id or 'NA'}-{datetime.utcnow():%Y%m%d%H%M%S}-{suffix}"

    def _normalize_status(self, status: Any) -> str:
        value = str(status or "PENDING").upper()
        if value in {"APPROVED", "SALE_APPROVED", "PAYMENT_APPROVED", "APROBADO"}:
            return "APROBADO"
        if value in {"REJECTED", "DECLINED", "FAILED", "RECHAZADO"}:
            return "RECHAZADO"
        if value in {"EXPIRED", "EXPIRADO"}:
            return "EXPIRADO"
        return "PENDIENTE"

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


class BoldSimpleCheckoutService:
    def __init__(self, session: AsyncSession):
        self.repo = BoldQrTestRepository(session)

    async def create_button_config(
        self,
        *,
        amount: Decimal,
        currency: str,
        order_id: str | None,
        description: str | None,
        redirection_url: str | None,
        button_style: str,
        tax: str | None,
        customer_data: dict[str, Any] | None,
        billing_address: dict[str, Any] | None,
        origin_url: str | None,
        expiration_date: str | None,
        extra_data_1: str | None,
        extra_data_2: str | None,
        cajero_id: int | None,
    ) -> dict[str, Any]:
        api_key = settings.bold_checkout_api_key or settings.bold_api_key
        secret_key = settings.bold_checkout_secret_key
        if not api_key:
            raise ValueError("BOLD_CHECKOUT_API_KEY o BOLD_API_KEY no está configurada")
        if not secret_key:
            raise ValueError("BOLD_CHECKOUT_SECRET_KEY no está configurada")

        normalized_currency = currency.upper()
        if normalized_currency not in {"COP", "USD"}:
            raise ValueError("La moneda debe ser COP o USD")

        normalized_amount = amount.quantize(Decimal("1"))
        if normalized_amount != amount:
            raise ValueError("El monto no debe tener decimales")
        if normalized_amount < Decimal("1000"):
            raise ValueError("El monto mínimo es 1000")

        reference = order_id or self._build_simple_order_id()
        if not ORDER_ID_PATTERN.fullmatch(reference):
            raise ValueError("order_id solo acepta letras, números, guiones y guiones bajos; máximo 60 caracteres")

        self._validate_description(description)
        self._validate_url(redirection_url, "redirection_url")
        self._validate_url(origin_url, "origin_url")
        self._validate_button_style(button_style)
        self._validate_tax(tax)

        amount_int = int(normalized_amount)
        signature = self._build_integrity_signature(
            order_id=reference,
            amount=amount_int,
            currency=normalized_currency,
            secret_key=secret_key,
        )
        attributes = self._build_attributes(
            api_key=api_key,
            button_style=button_style,
            order_id=reference,
            amount=amount_int,
            currency=normalized_currency,
            signature=signature,
            description=description,
            redirection_url=redirection_url,
            tax=tax,
            customer_data=customer_data,
            billing_address=billing_address,
            origin_url=origin_url,
            expiration_date=expiration_date,
            extra_data_1=extra_data_1,
            extra_data_2=extra_data_2,
        )
        payment = await self.repo.add(
            BoldQrPagoIndependienteORM(
                orden_id=0,
                mesa_id=None,
                cajero_id=cajero_id,
                monto=amount_int,
                moneda=normalized_currency,
                referencia=reference,
                bold_payment_id=None,
                estado="PENDIENTE",
                metodo_pago="BOTON_BOLD",
                qr_payload=None,
                qr_url=None,
                confirmado_en_pos=0,
            )
        )
        return {
            "id": payment.id,
            "estado": payment.estado,
            "checkout_script_url": CHECKOUT_SCRIPT_URL,
            "order_id": reference,
            "amount": amount_int,
            "currency": normalized_currency,
            "integrity_signature": signature,
            "button_style": button_style,
            "attributes": attributes,
            "script_html": self._build_script_html(attributes),
        }

    def _build_integrity_signature(self, *, order_id: str, amount: int, currency: str, secret_key: str) -> str:
        raw_signature = f"{order_id}{amount}{currency}{secret_key}"
        return hashlib.sha256(raw_signature.encode("utf-8")).hexdigest()

    def _build_simple_order_id(self) -> str:
        suffix = uuid4().hex[:8].upper()
        return f"SIMPLE-{datetime.utcnow():%Y%m%d%H%M%S}-{suffix}"

    def _build_attributes(
        self,
        *,
        api_key: str,
        button_style: str,
        order_id: str,
        amount: int,
        currency: str,
        signature: str,
        description: str | None,
        redirection_url: str | None,
        tax: str | None,
        customer_data: dict[str, Any] | None,
        billing_address: dict[str, Any] | None,
        origin_url: str | None,
        expiration_date: str | None,
        extra_data_1: str | None,
        extra_data_2: str | None,
    ) -> dict[str, str]:
        attributes = {
            "data-bold-button": button_style,
            "data-api-key": api_key,
            "data-order-id": order_id,
            "data-currency": currency,
            "data-amount": str(amount),
            "data-integrity-signature": signature,
        }
        optional_values = {
            "data-redirection-url": redirection_url,
            "data-description": description,
            "data-tax": tax,
            "data-expiration-date": expiration_date,
            "data-origin-url": origin_url,
            "data-extra-data-1": extra_data_1,
            "data-extra-data-2": extra_data_2,
        }
        for key, value in optional_values.items():
            if value:
                attributes[key] = value
        if customer_data:
            attributes["data-customer-data"] = json.dumps(customer_data, separators=(",", ":"))
        if billing_address:
            attributes["data-billing-address"] = json.dumps(billing_address, separators=(",", ":"))
        return attributes

    def _build_script_html(self, attributes: dict[str, str]) -> str:
        lines = ["<script", f'  src="{CHECKOUT_SCRIPT_URL}"']
        for key, value in attributes.items():
            escaped_value = value.replace("&", "&amp;").replace('"', "&quot;")
            lines.append(f'  {key}="{escaped_value}"')
        lines.append("></script>")
        return "\n".join(lines)

    def _validate_button_style(self, button_style: str) -> None:
        if button_style not in {"dark-S", "dark-M", "dark-L", "light-S", "light-M", "light-L"}:
            raise ValueError("button_style debe ser dark-S, dark-M, dark-L, light-S, light-M o light-L")

    def _validate_description(self, description: str | None) -> None:
        if description and URL_PATTERN.search(description):
            raise ValueError("La descripción no puede contener URLs")

    def _validate_tax(self, tax: str | None) -> None:
        if not tax:
            return
        allowed = {"vat-5", "vat-19", "iac-8", "consumption"}
        if tax in allowed:
            return
        try:
            Decimal(tax)
            return
        except Exception:
            pass
        try:
            parsed = json.loads(tax)
        except json.JSONDecodeError as exc:
            raise ValueError("tax debe ser vat-5, vat-19, iac-8, consumption, número o JSON válido") from exc
        if not isinstance(parsed, dict):
            raise ValueError("tax en formato JSON debe ser un objeto")

    def _validate_url(self, url: str | None, field_name: str) -> None:
        if not url:
            return
        if "127.0.0.1" in url:
            raise ValueError(f"{field_name} debe usar localhost en vez de 127.0.0.1")
        if url.startswith("https://") or url.startswith("http://localhost"):
            return
        raise ValueError(f"{field_name} debe iniciar con https:// o http://localhost para pruebas locales")
