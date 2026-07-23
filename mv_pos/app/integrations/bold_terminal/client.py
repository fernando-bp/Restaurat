from __future__ import annotations

from typing import Any
import httpx


class BoldTerminalError(RuntimeError):
    def __init__(self, message: str, code: str | None = None):
        super().__init__(message)
        self.code = code


class BoldTerminalClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url, self.api_key = base_url.rstrip("/"), api_key

    @property
    def headers(self):
        return {"Authorization": f"x-api-key {self.api_key}", "Content-Type": "application/json"}

    async def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        if not self.api_key:
            raise BoldTerminalError("Bold POS no está configurado.")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(method, f"{self.base_url}{path}", headers=self.headers, **kwargs)
        body = response.json() if response.content else {}
        if response.status_code >= 400:
            errors = body.get("errors") or []
            code = (errors[0].get("code") if errors and isinstance(errors[0], dict) else None)
            raise BoldTerminalError("Bold rechazó la solicitud.", code)
        return body

    async def availability(self):
        methods, terminals = await self._request("GET", "/payments/payment-methods"), await self._request("GET", "/payments/binded-terminals")
        enabled = any(item.get("name") == "POS" and item.get("enabled") for item in methods.get("payload", {}).get("payment_methods", []))
        available = [item for item in terminals.get("payload", {}).get("available_terminals", []) if item.get("status") == "BINDED"]
        return {"pos_enabled": enabled, "terminals": available}

    async def checkout(self, payload: dict[str, Any]):
        return await self._request("POST", "/payments/app-checkout", json=payload)

    async def notification(self, reference: str):
        return await self._request("GET", f"/payments/webhook/notifications/{reference}?is_external_reference=true")
