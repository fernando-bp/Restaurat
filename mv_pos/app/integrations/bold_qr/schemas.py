from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class BoldQrIntentCreateDTO(BaseModel):
    orden_id: int = Field(..., gt=0)
    mesa_id: int | None = Field(None, gt=0)
    monto: Decimal | None = Field(None, gt=0)
    payer_name: str | None = None


class BoldQrIntentResponseDTO(BaseModel):
    id: int
    orden_id: int
    mesa_id: int | None
    monto: Decimal
    moneda: str
    referencia: str
    bold_payment_id: str | None
    estado: str
    metodo_pago: str
    qr_payload: str | None
    expires_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class BoldSimpleCheckoutCreateDTO(BaseModel):
    amount: Decimal = Field(..., ge=1000)
    currency: str = Field("COP", min_length=3, max_length=3)
    order_id: str | None = Field(None, max_length=60)
    description: str | None = Field(None, min_length=2, max_length=100)
    redirection_url: str | None = None
    button_style: str = "dark-L"
    tax: str | None = None
    customer_data: dict[str, Any] | None = None
    billing_address: dict[str, Any] | None = None
    origin_url: str | None = None
    expiration_date: str | None = None
    extra_data_1: str | None = None
    extra_data_2: str | None = None


class BoldSimpleCheckoutResponseDTO(BaseModel):
    id: int
    estado: str
    checkout_script_url: str
    order_id: str
    amount: int
    currency: str
    integrity_signature: str
    button_style: str
    attributes: dict[str, str]
    script_html: str


class BoldWebhookResponseDTO(BaseModel):
    ok: bool
    status: str
    intent_id: int | None = None
    message: str | None = None


class BoldWebhookEventDTO(BaseModel):
    id: str | None = None
    type: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
