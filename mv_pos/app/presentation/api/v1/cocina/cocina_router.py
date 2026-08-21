from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.mesa import OrdenORM
from app.infrastructure.database.models.orden_item import OrdenItemORM
from app.infrastructure.database.models.receta import RecetaORM
from app.presentation.dependencies.auth_deps import get_current_user
from app.presentation.dependencies.db_deps import get_db_session

cocina_router = APIRouter(prefix="/cocina", tags=["cocina"])

_ESTADOS_ACTIVOS = ("en_preparacion",)


@cocina_router.get("/comandas", summary="Listar comandas activas para cocina", status_code=200)
async def listar_comandas(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    restaurante_id = current_user.get("restaurante_id") or 1

    ordenes_result = await db.execute(
        select(OrdenORM)
        .where(OrdenORM.restaurante_id == restaurante_id)
        .where(OrdenORM.estado.in_(("abierta", "en_preparacion", "lista")))
    )
    ordenes = ordenes_result.scalars().all()

    comandas = []
    for orden in ordenes:
        items_result = await db.execute(
            select(OrdenItemORM)
            .where(OrdenItemORM.orden_id == orden.id)
            .where(OrdenItemORM.estado == "en_preparacion")
        )
        items = items_result.scalars().all()

        if not items:
            continue

        mesa = orden.mesa
        items_data = []
        for item in items:
            receta_result = await db.execute(
                select(RecetaORM).where(RecetaORM.id == item.receta_id)
            )
            receta = receta_result.scalar_one_or_none()
            items_data.append(
                {
                    "item_id": item.id,
                    "receta_id": item.receta_id,
                    "receta_nombre": receta.nombre if receta else f"Receta #{item.receta_id}",
                    "cantidad": item.cantidad,
                    "estado": item.estado,
                    "notas": item.notas or item.modificadores or "",
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                }
            )

        comandas.append(
            {
                "orden_id": orden.id,
                "mesa_id": orden.mesa_id,
                "mesa_numero": mesa.numero if mesa else str(orden.mesa_id),
                "num_comensales": orden.num_comensales,
                "hora_confirmacion": (
                    orden.hora_confirmacion.isoformat() if orden.hora_confirmacion else None
                ),
                "notas_generales": orden.notas_generales or "",
                "items": items_data,
            }
        )

    return {"comandas": sorted(comandas, key=lambda c: c["hora_confirmacion"] or "")}


@cocina_router.patch(
    "/items/{item_id}/listo",
    summary="Marcar ítem de comanda como listo",
    status_code=200,
)
async def marcar_item_listo(
    item_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    item_result = await db.execute(select(OrdenItemORM).where(OrdenItemORM.id == item_id))
    item = item_result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ítem no encontrado")

    if item.estado != "en_preparacion":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El ítem está en estado '{item.estado}', no se puede marcar como listo",
        )

    item.estado = "listo"
    item.hora_lista = datetime.utcnow()
    item.cocinero_id = current_user.get("id")
    db.add(item)
    await db.flush()

    remaining_result = await db.execute(
        select(OrdenItemORM)
        .where(OrdenItemORM.orden_id == item.orden_id)
        .where(OrdenItemORM.estado == "en_preparacion")
    )
    remaining = remaining_result.scalars().all()

    if not remaining:
        orden_result = await db.execute(select(OrdenORM).where(OrdenORM.id == item.orden_id))
        orden = orden_result.scalar_one_or_none()
        if orden and orden.estado == "en_preparacion":
            orden.estado = "lista"
            db.add(orden)

    await db.commit()
    return {"mensaje": "Ítem marcado como listo", "item_id": item_id, "todos_listos": not remaining}
