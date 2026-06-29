from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx


class BoldQrTestClientError(RuntimeError):
    pass


class BoldQrTestClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"x-api-key {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_payment_intent(
        self,
        *,
        amount: Decimal,
        reference: str,
        description: str | None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise BoldQrTestClientError("BOLD_API_KEY no esta configurada")

        payload: dict[str, Any] = {
            "reference_id": reference,
            "amount": {"currency": "COP", "total_amount": int(amount)},
            "description": description or f"Prueba QR Bre-B monto ${int(amount)}",
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.base_url}/v1/payment-intent",
                json=payload,
                headers=self._headers(),
            )

        if response.status_code not in (200, 201):
            raise BoldQrTestClientError(f"Bold rechazo la intencion de pago: {response.text}")
        return response.json()

    async def create_qr_payment(self, *, reference: str) -> dict[str, Any]:
        if not self.api_key:
            raise BoldQrTestClientError("BOLD_API_KEY no esta configurada")

        payload: dict[str, Any] = {
            "reference_id": reference,
            "payer": {
                "person_type": "NATURAL_PERSON",
                "name": "Cliente POS",
                "phone": "3000000000",
                "email": "pos@comercio.co",
                "document_type": "CEDULA",
                "document_number": "1000000000",
            },
            "payment_method": {
                "name": "QR",
                "qr_format": "IMAGE",
            },
            "device_fingerprint": {
                "device_type": "DESKTOP",
                "os": "Windows",
                "browser": "Chrome",
                "java_enabled": False,
                "language": "es-CO",
                "color_depth": 24,
                "screen_height": 1080,
                "screen_width": 1920,
                "time_zone_offset": 300,
            },
        }

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.base_url}/v1/payment",
                json=payload,
                headers=self._headers(),
            )

        if response.status_code not in (200, 201):
            raise BoldQrTestClientError(f"Bold rechazo el intento de pago QR: {response.text}")
        return response.json()
