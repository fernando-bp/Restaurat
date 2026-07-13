from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.config import settings


class FactusAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload or {}


class FactusClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or settings.factus_api_base_url).rstrip("/")
        self.timeout = timeout or settings.factus_timeout_seconds
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._token_expires_at: datetime | None = None
        self._token_lock = asyncio.Lock()

    async def get_access_token(self) -> str:
        async with self._token_lock:
            if self._access_token and self._token_expires_at and self._token_expires_at > datetime.now(timezone.utc):
                return self._access_token

            if self._refresh_token:
                try:
                    await self.refresh_access_token()
                except Exception:
                    self._refresh_token = None

            if self._access_token and self._token_expires_at and self._token_expires_at > datetime.now(timezone.utc):
                return self._access_token

            payload: dict[str, str] = {
                "grant_type": settings.factus_grant_type,
                "client_id": settings.factus_client_id,
                "client_secret": settings.factus_client_secret,
            }

            if settings.factus_grant_type == "password":
                if not settings.factus_username or not settings.factus_password:
                    raise RuntimeError("Factus username/password are required for password grant")
                payload.update({
                    "username": settings.factus_username,
                    "password": settings.factus_password,
                })

            if not settings.factus_client_id or not settings.factus_client_secret:
                raise RuntimeError("Factus credentials are not configured")

            # Debug: mask client_secret when printing
            def _mask(s: str | None) -> str:
                if not s:
                    return ""
                return s[:4] + "..."

            # Send multipart/form-data without HTTP Basic auth (match successful curl/Postman request)
            masked = {k: (v if k != 'client_secret' else _mask(settings.factus_client_secret)) for k, v in payload.items()}
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    print("Factus token request ->", f"url={self.base_url}/oauth/token", "payload=", masked, "auth=None")
                    files_payload = {k: (None, v) for k, v in payload.items()}
                    response = await client.post(
                        f"{self.base_url}/oauth/token",
                        files=files_payload,
                        headers={"Accept": "application/json"},
                    )
                    response.raise_for_status()
                    data = response.json()
                except Exception:
                    try:
                        content = response.text
                        status = response.status_code
                    except Exception:
                        content = None
                        status = None
                    print("Factus token request failed -> status=", status, "response=", content)
                    raise

            self._access_token = str(data.get("access_token") or "")
            self._refresh_token = str(data.get("refresh_token") or "") if data.get("refresh_token") else None
            expires_in = int(data.get("expires_in") or 3600)
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(expires_in - 60, 300))
            if not self._access_token:
                raise RuntimeError("Factus did not return an access token")
            return self._access_token

    async def refresh_access_token(self) -> str:
        if not self._refresh_token:
            raise RuntimeError("No refresh token available for Factus")

        payload: dict[str, str] = {
            "grant_type": "refresh_token",
            "refresh_token": self._refresh_token,
        }

        if not settings.factus_client_id or not settings.factus_client_secret:
            raise RuntimeError("Factus credentials are not configured")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                masked = {k: ("..." if k == "refresh_token" else v) for k, v in payload.items()}
                print("Factus refresh request ->", f"url={self.base_url}/oauth/token", "payload=", masked, "auth=None")
                files_payload = {k: (None, v) for k, v in payload.items()}
                response = await client.post(
                    f"{self.base_url}/oauth/token",
                    files=files_payload,
                    headers={
                        "Accept": "application/json",
                    },
                )
                response.raise_for_status()
                data = response.json()
            except Exception:
                try:
                    print("Factus refresh failed -> status=", response.status_code, "response=", response.text)
                except Exception:
                    pass
                raise

        self._access_token = str(data.get("access_token") or "")
        self._refresh_token = str(data.get("refresh_token") or self._refresh_token) if data.get("refresh_token") else self._refresh_token
        expires_in = int(data.get("expires_in") or 3600)
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=max(expires_in - 60, 300))
        if not self._access_token:
            raise RuntimeError("Factus did not return an access token")
        return self._access_token

    async def post_invoice(self, payload: dict[str, Any]) -> dict[str, Any]:
        token = await self.get_access_token()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/v2/bills/validate",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                try:
                    payload = response.json()
                except ValueError:
                    payload = {}
                detail = payload or response.text
                raise FactusAPIError(
                    f"Factus rejected request: {detail}",
                    status_code=response.status_code,
                    payload=payload,
                ) from exc
            return response.json()

    async def get_invoice_by_reference(self, reference_code: str) -> dict[str, Any]:
        token = await self.get_access_token()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/v2/bills/reference/{reference_code}",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                try:
                    payload = response.json()
                except ValueError:
                    payload = {}
                detail = payload or response.text
                raise FactusAPIError(
                    f"Factus rejected invoice lookup: {detail}",
                    status_code=response.status_code,
                    payload=payload,
                ) from exc
            return response.json()

    async def list_numbering_ranges(
        self,
        *,
        range_id: int | None = None,
        document: str | None = None,
        resolution_number: str | None = None,
        technical_key: str | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any]:
        token = await self.get_access_token()
        params: dict[str, str | int] = {}
        if range_id is not None:
            params["filter[id]"] = range_id
        if document:
            params["filter[document]"] = document
        if resolution_number:
            params["filter[resolution_number]"] = resolution_number
        if technical_key:
            params["filter[technical_key]"] = technical_key
        if is_active is not None:
            params["filter[is_active]"] = 1 if is_active else 0

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/v2/numbering-ranges",
                params=params,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                detail = response.text
                raise RuntimeError(f"Factus rejected numbering ranges request: {detail}") from exc
            return response.json()
