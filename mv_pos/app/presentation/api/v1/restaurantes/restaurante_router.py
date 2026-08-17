from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.database.models.restaurante import RestauranteORM
from app.presentation.dependencies.db_deps import get_db_session

restaurante_router = APIRouter(prefix="/restaurantes", tags=["restaurantes (admin)"])


# ── Schemas ────────────────────────────────────────────────────────────────────

class CrearRestauranteRequest(BaseModel):
    slug: str = Field(..., example="pizza-palace", description="Identificador URL-friendly, único")
    nombre: str = Field(..., example="Pizza Palace")
    r2_prefix: str = Field(
        default="",
        example="tenants/pizza-palace/",
        description="Prefijo en el bucket R2 para imágenes de este restaurante.",
    )


class RestauranteResponse(BaseModel):
    id: int
    slug: str
    nombre: str
    r2_prefix: str
    activo: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Dependency de autenticación ────────────────────────────────────────────────

async def _check_superadmin(x_superadmin_key: Optional[str] = Header(None, alias="X-Superadmin-Key")) -> None:
    if not settings.superadmin_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SUPERADMIN_API_KEY no configurada en el servidor",
        )
    if x_superadmin_key != settings.superadmin_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clave de superadmin inválida o ausente",
        )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@restaurante_router.post(
    "/",
    response_model=RestauranteResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_check_superadmin)],
    summary="Registrar un nuevo restaurante",
)
async def crear_restaurante(
    payload: CrearRestauranteRequest,
    db: AsyncSession = Depends(get_db_session),
) -> RestauranteResponse:
    """
    Onboarding de un nuevo restaurante en el sistema compartido.

    Solo inserta la fila en la tabla "restaurantes" del DB compartido.
    Las tablas (mesas, usuarios, recetas, etc.) ya existen — todos los restaurantes
    las comparten y se aíslan por la columna restaurante_id.

    Después de esto: crear usuarios vía POST /api/v1/usuarios
    y hacer login con tenant_slug = payload.slug.
    """
    existing = await db.execute(
        select(RestauranteORM).where(RestauranteORM.slug == payload.slug)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El slug '{payload.slug}' ya está en uso",
        )

    orm = RestauranteORM(
        slug=payload.slug,
        nombre=payload.nombre,
        r2_prefix=payload.r2_prefix or f"tenants/{payload.slug}/",
    )
    db.add(orm)
    await db.commit()
    await db.refresh(orm)
    return orm


@restaurante_router.get(
    "/",
    response_model=List[RestauranteResponse],
    dependencies=[Depends(_check_superadmin)],
    summary="Listar todos los restaurantes",
)
async def listar_restaurantes(
    db: AsyncSession = Depends(get_db_session),
) -> List[RestauranteResponse]:
    result = await db.execute(select(RestauranteORM).order_by(RestauranteORM.created_at))
    return list(result.scalars().all())


@restaurante_router.patch(
    "/{restaurante_id}/desactivar",
    dependencies=[Depends(_check_superadmin)],
    summary="Desactivar un restaurante",
)
async def desactivar_restaurante(
    restaurante_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    result = await db.execute(
        select(RestauranteORM).where(RestauranteORM.id == restaurante_id)
    )
    orm = result.scalar_one_or_none()
    if not orm:
        raise HTTPException(status_code=404, detail="Restaurante no encontrado")

    orm.activo = False
    await db.commit()
    return {"detail": f"Restaurante '{orm.slug}' desactivado."}
