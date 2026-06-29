from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class BoldQrTestCreateDTO(BaseModel):
    monto: Decimal = Field(..., gt=0)
    descripcion: str | None = None


class BoldQrTestResponseDTO(BaseModel):
    id: int
    orden_id: int | None
    mesa_id: int | None
    cajero_id: int | None
    monto: Decimal
    moneda: str
    referencia: str
    bold_payment_id: str | None
    estado: str
    metodo_pago: str
    qr_payload: str | None
    qr_url: str | None
    webhook_id: str | None
    ultimo_error: str | None
    confirmado_en_pos: int
    pago_pos_id: int | None
    created_at: datetime
    expires_at: datetime | None
    approved_at: datetime | None

    class Config:
        from_attributes = True


class BoldQrTestWebhookDTO(BaseModel):
    ok: bool
    status: str
    payment_id: str | None = None
    reference: str | None = None
