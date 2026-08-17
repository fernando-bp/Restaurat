from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.inventario import InventarioORM
from app.infrastructure.database.models.ingrediente import IngredienteORM
from app.infrastructure.database.models.movimientos_inventario import MovimientosInventarioORM
from app.presentation.dependencies.auth_deps import get_current_user
from app.presentation.dependencies.db_deps import get_db_session
from app.application.dtos.inventario_dto import ActualizarStockRequest, InventarioItemDTO

inventario_router = APIRouter(prefix="/inventario", tags=["inventario"])


def serializar_inventario(inventario: InventarioORM) -> InventarioItemDTO:
    ingrediente = inventario.ingrediente
    unidad = ingrediente.unidad.abreviatura if ingrediente and ingrediente.unidad else None
    return InventarioItemDTO(
        id=inventario.id,
        ingrediente_id=inventario.ingrediente_id,
        nombre_ingrediente=ingrediente.nombre if ingrediente else 'Desconocido',
        stock_actual=float(inventario.stock_actual),
        stock_minimo=float(inventario.stock_minimo),
        stock_maximo=float(inventario.stock_maximo) if inventario.stock_maximo is not None else None,
        unidad=unidad,
        ubicacion=inventario.ubicacion,
        esta_en_alerta=float(inventario.stock_actual) <= float(inventario.stock_minimo),
    )


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

    result = await db.execute(
        select(InventarioORM)
        .join(IngredienteORM, IngredienteORM.id == InventarioORM.ingrediente_id)
        .where(IngredienteORM.restaurante_id == current_user["restaurante_id"])
    )
    registros = result.scalars().all()

    return [serializar_inventario(inventario) for inventario in registros]


@inventario_router.patch(
    "/{inventario_id}/stock",
    response_model=InventarioItemDTO,
    summary="Actualizar el stock actual de un ingrediente",
)
async def actualizar_stock(
    inventario_id: int,
    request: ActualizarStockRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> InventarioItemDTO:
    if current_user.get('rol') not in ('chef', 'administrador', 'admin'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    result = await db.execute(
        select(InventarioORM)
        .join(IngredienteORM, IngredienteORM.id == InventarioORM.ingrediente_id)
        .where(
            InventarioORM.id == inventario_id,
            IngredienteORM.restaurante_id == current_user["restaurante_id"],
        )
    )
    inventario = result.scalar_one_or_none()
    if inventario is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registro de inventario no encontrado")

    stock_anterior = float(inventario.stock_actual)
    nuevo_stock = float(request.stock_actual)
    tipo_movimiento = "ajuste_positivo" if nuevo_stock >= stock_anterior else "ajuste_negativo"
    inventario.stock_actual = nuevo_stock
    db.add(MovimientosInventarioORM(
        ingrediente_id=inventario.ingrediente_id,
        tipo=tipo_movimiento,
        cantidad=abs(nuevo_stock - stock_anterior),
        stock_resultante=nuevo_stock,
        precio_unitario_snap=float(inventario.ingrediente.precio_unitario) if inventario.ingrediente else None,
        motivo=request.motivo or f"Ajuste manual de {stock_anterior} a {nuevo_stock}",
        usuario_id=int(current_user["id"]),
    ))
    await db.commit()
    await db.refresh(inventario)
    return serializar_inventario(inventario)
