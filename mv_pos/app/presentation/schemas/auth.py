from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    username: str = Field(..., example="juan")
    password: str = Field(..., min_length=8)
    remember_me: bool = Field(False)


class UserPublic(BaseModel):
    id: int
    nombre_completo: str
    username: str
    rol: Optional[str] = None


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user: UserPublic


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
