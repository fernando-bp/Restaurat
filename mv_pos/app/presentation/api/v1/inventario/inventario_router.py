from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.inventario import InventarioORM
from app.presentation.dependencies.auth_deps import get_current_user
from app.presentation.dependencies.db_deps import get_db_session
from app.application.dtos.inventario_dto import InventarioItemDTO

inventario_router = APIRouter(prefix="/inventario", tags=["inventario"])


@inventario_router.get(
    "/",
    response_model=List[InventarioItemDTO],
    summary="Listar inventario de ingredientes",
    description="Devuelve el stock actual y datos de cada ingrediente en inventario.",
)
async def listar_inventario(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[InventarioItemDTO]:
    if current_user.get('rol') not in ('chef', 'administrador', 'admin'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    result = await db.execute(select(InventarioORM))
    registros = result.scalars().all()

    return [
        InventarioItemDTO(
            id=inventario.id,
            ingrediente_id=inventario.ingrediente_id,
            nombre_ingrediente=(inventario.ingrediente.nombre if inventario.ingrediente is not None else 'Desconocido'),
            stock_actual=float(inventario.stock_actual),
            stock_minimo=float(inventario.stock_minimo),
            stock_maximo=float(inventario.stock_maximo) if inventario.stock_maximo is not None else None,
            ubicacion=inventario.ubicacion,
            esta_en_alerta=float(inventario.stock_actual) <= float(inventario.stock_minimo),
        )
        for inventario in registros
    ]
