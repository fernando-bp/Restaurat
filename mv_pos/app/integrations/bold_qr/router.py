from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.integrations.bold_qr.client import BoldClientError
from app.integrations.bold_qr.schemas import (
    BoldQrIntentCreateDTO,
    BoldQrIntentResponseDTO,
    BoldSimpleCheckoutCreateDTO,
    BoldSimpleCheckoutResponseDTO,
    BoldWebhookResponseDTO,
)
from app.integrations.bold_qr.security import verify_bold_signature
from app.integrations.bold_qr.service import BoldQrService, BoldSimpleCheckoutService
from app.presentation.dependencies.auth_deps import get_current_user
from app.presentation.dependencies.db_deps import get_db_session

bold_qr_router = APIRouter(prefix="/bold-qr", tags=["bold-qr"])


@bold_qr_router.post("/checkout/simple", response_model=BoldSimpleCheckoutResponseDTO, status_code=201)
async def create_simple_bold_checkout(
    payload: BoldSimpleCheckoutCreateDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BoldSimpleCheckoutResponseDTO:
    if current_user.get("rol") not in ("cajero", "administrador", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    try:
        checkout = await BoldSimpleCheckoutService(db).create_button_config(
            amount=payload.amount,
            currency=payload.currency,
            order_id=payload.order_id,
            description=payload.description,
            redirection_url=payload.redirection_url,
            button_style=payload.button_style,
            tax=payload.tax,
            customer_data=payload.customer_data,
            billing_address=payload.billing_address,
            origin_url=payload.origin_url,
            expiration_date=payload.expiration_date,
            extra_data_1=payload.extra_data_1,
            extra_data_2=payload.extra_data_2,
            cajero_id=current_user.get("id"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return BoldSimpleCheckoutResponseDTO(**checkout)


@bold_qr_router.post("/intents", response_model=BoldQrIntentResponseDTO, status_code=201)
async def create_bold_qr_intent(
    payload: BoldQrIntentCreateDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BoldQrIntentResponseDTO:
    if current_user.get("rol") not in ("cajero", "administrador", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    service = BoldQrService(db)
    try:
        intent = await service.create_intent(
            orden_id=payload.orden_id,
            mesa_id=payload.mesa_id,
            monto=payload.monto,
            cajero_id=current_user.get("id"),
            payer_name=payload.payer_name,
        )
    except BoldClientError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return BoldQrIntentResponseDTO.model_validate(intent)


@bold_qr_router.get("/intents/{intent_id}", response_model=BoldQrIntentResponseDTO)
async def get_bold_qr_intent(
    intent_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> BoldQrIntentResponseDTO:
    if current_user.get("rol") not in ("cajero", "administrador", "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    intent = await BoldQrService(db).get_intent(intent_id)
    if not intent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Intención Bold no encontrada")
    return BoldQrIntentResponseDTO.model_validate(intent)


@bold_qr_router.post("/webhook", response_model=BoldWebhookResponseDTO)
async def receive_bold_webhook(
    request: Request,
    x_bold_signature: str | None = Header(None),
    db: AsyncSession = Depends(get_db_session),
) -> BoldWebhookResponseDTO:
    raw_body = await request.body()
    if settings.bold_webhook_verify_signature:
        if not verify_bold_signature(raw_body, x_bold_signature, settings.bold_webhook_secret):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Firma Bold inválida")

    try:
        event = json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON inválido") from exc

    service = BoldQrService(db)
    try:
        intent, result = await service.process_webhook(event)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return BoldWebhookResponseDTO(
        ok=True,
        status=result,
        intent_id=intent.id if intent else None,
        message="Webhook procesado",
    )
