from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.bold_qr_test.client import BoldQrTestClientError
from app.integrations.bold_qr_test.schemas import (
    BoldQrTestCreateDTO,
    BoldQrTestResponseDTO,
    BoldQrTestWebhookDTO,
)
from app.integrations.bold_qr_test.security import verify_bold_signature
from app.integrations.bold_qr_test.service import BoldQrTestService
from app.presentation.dependencies.auth_deps import get_current_user
from app.presentation.dependencies.db_deps import get_db_session

bold_qr_test_router = APIRouter(prefix="/bold-test", tags=["bold-test"])


@bold_qr_test_router.post("/qr", response_model=BoldQrTestResponseDTO, status_code=201)
async def create_test_qr_payment(
    payload: BoldQrTestCreateDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BoldQrTestResponseDTO:
    if current_user.get("rol") not in ("cajero", "administrador", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    try:
        payment = await BoldQrTestService(db).create_payment(
            monto=payload.monto,
            cajero_id=current_user.get("id"),
            descripcion=payload.descripcion,
        )
    except BoldQrTestClientError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return BoldQrTestResponseDTO.model_validate(payment)


@bold_qr_test_router.get("/qr/{payment_id}", response_model=BoldQrTestResponseDTO)
async def get_test_qr_payment(
    payment_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BoldQrTestResponseDTO:
    if current_user.get("rol") not in ("cajero", "administrador", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    payment = await BoldQrTestService(db).get_payment(payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pago Bold de prueba no encontrado")
    return BoldQrTestResponseDTO.model_validate(payment)


@bold_qr_test_router.post("/webhook", response_model=BoldQrTestWebhookDTO)
async def receive_test_bold_webhook(
    request: Request,
    x_bold_signature: str | None = Header(None),
    db: AsyncSession = Depends(get_db_session),
) -> BoldQrTestWebhookDTO:
    raw_body = await request.body()
    if settings.bold_webhook_verify_signature:
        if not verify_bold_signature(raw_body, x_bold_signature, settings.bold_webhook_secret):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Firma Bold invalida")

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError:
        return BoldQrTestWebhookDTO(ok=True, status="invalid_json")

    payment, result = await BoldQrTestService(db).process_webhook_fast(event)
    data = event.get("data") or {}
    metadata = data.get("metadata") or {}
    return BoldQrTestWebhookDTO(
        ok=True,
        status=result,
        payment_id=data.get("payment_id") or event.get("subject"),
        reference=metadata.get("reference") or data.get("reference") or (payment.referencia if payment else None),
    )
