from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.enums.forma_pago import FormaPagoEnum
from app.infrastructure.database.models.mesa import MesaORM, OrdenORM
from app.infrastructure.database.models.pago import PagoORM
from app.integrations.bold_terminal.client import BoldTerminalClient, BoldTerminalError
from app.integrations.bold_terminal.models import BoldTerminalPaymentORM
from app.presentation.dependencies.auth_deps import get_current_user
from app.presentation.dependencies.db_deps import get_db_session

router = APIRouter(prefix="/bold-terminal", tags=["bold-terminal"])
webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


class CheckoutPayload(BaseModel):
    """The server calculates both total and tax from the persisted order."""

    orden_id: int
    mesa_id: int
    descripcion: str = Field(min_length=1, max_length=300)


def _client() -> BoldTerminalClient:
    return BoldTerminalClient(settings.bold_terminal_api_base_url, settings.bold_terminal_api_key)


def _require_pos_role(user: dict) -> None:
    if user.get("rol") not in ("cajero", "administrador", "admin"):
        raise HTTPException(403, "No autorizado")


def _error_detail(exc: BoldTerminalError) -> str:
    return {
        "AP003": "El pago con tarjeta no esta habilitado en Bold.",
        "AP004": "El datafono seleccionado no esta vinculado a la integracion.",
    }.get(exc.code, "No se pudo iniciar el pago, intenta de nuevo.")


def _verify(raw: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    expected = hmac.new(
        settings.bold_terminal_webhook_secret.encode(),
        base64.b64encode(raw),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature.removeprefix("sha256=").strip())


async def _get_payment(payment_id: int, user: dict, db: AsyncSession) -> BoldTerminalPaymentORM:
    payment = (await db.execute(
        select(BoldTerminalPaymentORM).where(BoldTerminalPaymentORM.id == payment_id)
    )).scalar_one_or_none()
    if not payment:
        raise HTTPException(404, "Pago Bold no encontrado")
    if user.get("rol") not in ("administrador", "admin") and payment.cajero_id != user.get("id"):
        raise HTTPException(403, "No autorizado para consultar este pago")
    return payment


async def _apply_bold_event(event: dict, db: AsyncSession) -> str:
    """Persist a webhook or fallback notification exactly once."""
    data, webhook_id = event.get("data") or {}, event.get("id")
    reference = (data.get("metadata") or {}).get("reference") or data.get("reference")
    payment_id = data.get("payment_id")
    if not reference:
        return "ignored"

    payment = (await db.execute(
        select(BoldTerminalPaymentORM).where(BoldTerminalPaymentORM.referencia == reference)
    )).scalar_one_or_none()
    if not payment:
        return "not_found"
    if payment.estado == "APROBADO" or (webhook_id and payment.webhook_id == webhook_id):
        return "duplicate"

    event_type = event.get("type")
    if event_type == "SALE_REJECTED":
        payment.estado = "RECHAZADO"
        payment.webhook_id = webhook_id or payment.webhook_id
        payment.payment_id = payment_id or payment.payment_id
        payment.ultimo_error = "Pago rechazado, intenta con otro metodo."
        await db.commit()
        return "rejected"
    if event_type != "SALE_APPROVED":
        return "ignored"

    amount = Decimal(str((data.get("amount") or {}).get("total", 0))).quantize(Decimal("1"))
    if amount != Decimal(payment.monto).quantize(Decimal("1")):
        raise HTTPException(400, "Monto del webhook no coincide con la orden")

    card_type = (data.get("card") or {}).get("card_type", "DEBIT").upper()
    payment_method = FormaPagoEnum.TARJETA_CREDITO if card_type == "CREDIT" else FormaPagoEnum.TARJETA_DEBITO
    terminal_reference = payment_id or payment.integration_id
    existing = (await db.execute(
        select(PagoORM).where(PagoORM.referencia_datafono == terminal_reference)
    )).scalar_one_or_none()
    if not existing:
        db.add(PagoORM(
            orden_id=payment.orden_id,
            forma_pago=payment_method.value,
            monto=payment.monto,
            referencia_datafono=terminal_reference,
            cajero_id=payment.cajero_id,
        ))

    orden = (await db.execute(select(OrdenORM).where(OrdenORM.id == payment.orden_id))).scalar_one()
    orden.estado, orden.hora_cierre = "pagada", datetime.utcnow()
    mesa = (await db.execute(select(MesaORM).where(MesaORM.id == orden.mesa_id))).scalar_one_or_none()
    if mesa:
        mesa.estado = "libre"
    payment.estado = "APROBADO"
    payment.webhook_id = webhook_id or payment.webhook_id
    payment.payment_id = payment_id or payment.payment_id
    payment.referencia_datafono = terminal_reference
    payment.ultimo_error = None
    await db.commit()
    return "approved"


@router.get("/availability")
async def availability(current_user: dict = Depends(get_current_user)):
    _require_pos_role(current_user)
    try:
        return await _client().availability()
    except BoldTerminalError as exc:
        return {"pos_enabled": False, "terminals": [], "message": str(exc)}


@router.post("/checkout", status_code=status.HTTP_201_CREATED)
async def checkout(
    payload: CheckoutPayload,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    _require_pos_role(current_user)
    orden = (await db.execute(select(OrdenORM).where(OrdenORM.id == payload.orden_id))).scalar_one_or_none()
    if not orden or orden.mesa_id != payload.mesa_id or orden.estado in ("pagada", "cancelada"):
        raise HTTPException(400, "La orden no esta disponible para pago.")

    monto = Decimal(orden.total_neto or 0).quantize(Decimal("1"))
    if monto <= 0:
        raise HTTPException(400, "La orden no tiene un saldo valido para cobrar.")
    pending = (await db.execute(select(BoldTerminalPaymentORM).where(
        BoldTerminalPaymentORM.orden_id == orden.id,
        BoldTerminalPaymentORM.estado == "PENDIENTE",
    ))).scalar_one_or_none()
    if pending:
        raise HTTPException(409, "Ya hay un pago en espera en el datafono para esta orden.")

    try:
        available = await _client().availability()
    except BoldTerminalError as exc:
        raise HTTPException(502, _error_detail(exc)) from exc
    if not available["pos_enabled"] or not available["terminals"]:
        raise HTTPException(409, "No hay un datafono Bold POS habilitado.")

    terminal = available["terminals"][0]
    reference = f"ORD-{orden.id}-{uuid4().hex[:12].upper()}"
    iva = Decimal(orden.total_iva or 0).quantize(Decimal("1"))
    taxes = [{"type": "VAT", "value": int(iva)}] if iva > 0 else []
    body = {
        "amount": {"currency": "COP", "taxes": taxes, "tip_amount": 0, "total_amount": int(monto)},
        "payment_method": "POS",
        "terminal_model": terminal["terminal_model"],
        "terminal_serial": terminal["terminal_serial"],
        "reference": reference,
        "user_email": f"{current_user.get('username') or 'cajero'}@magicvillage.local",
        "description": payload.descripcion,
    }
    try:
        response = await _client().checkout(body)
    except BoldTerminalError as exc:
        raise HTTPException(502, _error_detail(exc)) from exc
    integration_id = (response.get("payload") or {}).get("integration_id")
    if not integration_id:
        raise HTTPException(502, "Bold no devolvio un identificador de integracion.")

    payment = BoldTerminalPaymentORM(
        orden_id=orden.id, mesa_id=orden.mesa_id, cajero_id=current_user["id"], monto=monto,
        referencia=reference, integration_id=integration_id,
        terminal_model=terminal["terminal_model"], terminal_serial=terminal["terminal_serial"],
        payload=json.dumps(response),
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return {"id": payment.id, "reference": reference, "integration_id": integration_id, "estado": payment.estado}


@router.get("/payments/{payment_id}")
async def payment_status(payment_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    _require_pos_role(current_user)
    payment = await _get_payment(payment_id, current_user, db)
    return {"id": payment.id, "estado": payment.estado, "reference": payment.referencia, "ultimo_error": payment.ultimo_error}


@router.post("/payments/{payment_id}/verify")
async def verify_payment(payment_id: int, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    _require_pos_role(current_user)
    payment = await _get_payment(payment_id, current_user, db)
    try:
        result = await _client().notification(payment.referencia)
    except BoldTerminalError as exc:
        raise HTTPException(502, "No se pudo verificar el estado en Bold.") from exc
    notifications = result.get("notifications") or (result.get("payload") or {}).get("notifications") or []
    applied = "not_found"
    for event in notifications:
        applied = await _apply_bold_event(event, db)
        if applied in {"approved", "rejected", "duplicate"}:
            break
    await db.refresh(payment)
    return {"estado": payment.estado, "resultado": applied}


@webhook_router.post("/bold")
async def bold_webhook(request: Request, x_bold_signature: str | None = Header(None), db: AsyncSession = Depends(get_db_session)):
    raw = await request.body()
    if not _verify(raw, x_bold_signature):
        raise HTTPException(400, "Firma Bold invalida")
    try:
        event = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "JSON invalido") from exc
    return {"ok": True, "status": await _apply_bold_event(event, db)}
