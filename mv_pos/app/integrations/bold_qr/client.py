from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx


class BoldClientError(RuntimeError):
    pass


class BoldClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"x-api-key {self.api_key}",
            "Content-Type": "application/json",
        }

    async def create_qr_breb_intent(
        self,
        *,
        amount: Decimal,
        reference: str,
        payer_name: str | None,
    ) -> dict[str, Any]:
        if not self.api_key:
            raise BoldClientError("BOLD_API_KEY no está configurada")

        payload: dict[str, Any] = {
            "amount": {
                "currency": "COP",
                "total_amount": int(amount),
            },
            "reference": reference,
            "payment_method": {
                "type": "QR_BREB",
            },
        }
        if payer_name:
            payload["payer"] = {"name": payer_name}

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.base_url}/online/payments/v1/payment_intents",
                json=payload,
                headers=self._headers(),
            )

        if response.status_code >= 400:
            raise BoldClientError(f"Bold rechazó la intención QR: {response.text}")
        return response.json()

    async def get_payment_intent(self, bold_payment_id: str) -> dict[str, Any]:
        if not self.api_key:
            raise BoldClientError("BOLD_API_KEY no está configurada")

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.base_url}/online/payments/v1/payment_intents/{bold_payment_id}",
                headers=self._headers(),
            )

        if response.status_code >= 400:
            raise BoldClientError(f"No se pudo confirmar el pago en Bold: {response.text}")
        return response.json()
