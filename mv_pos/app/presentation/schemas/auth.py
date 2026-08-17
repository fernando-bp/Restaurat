from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., example="juan")
    password: str = Field(..., min_length=8)
    remember_me: bool = Field(False)
    tenant_slug: str = Field(
        ...,
        example="mi-restaurante",
        description=(
            "Identificador único del restaurante. "
            "El frontend lo extrae del subdominio automáticamente "
            "(ej: 'pizza-palace' de pizza-palace.mvpos.com). "
            "En localhost usa 'default'."
        ),
    )


class UserPublic(BaseModel):
    id: int
    nombre_completo: str
    username: str
    rol: Optional[str] = None
    restaurante_id: Optional[int] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user: UserPublic
    restaurante_slug: Optional[str] = None


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
