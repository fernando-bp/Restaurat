import base64


from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.presentation.dependencies.db_deps import get_db_session
from app.presentation.dependencies.auth_deps import get_current_pos_user
from app.domain.use_cases.crear_orden_uc import CrearOrdenUC
from app.domain.use_cases.confirmar_orden_uc import ConfirmarOrdenUC
from app.domain.use_cases.modificar_item_orden_uc import ModificarOrdenItemUC
from app.domain.use_cases.eliminar_item_orden_uc import EliminarOrdenItemUC
from app.infrastructure.repositories.mesa_repo_sqlalchemy import MesaRepoSQLAlchemy
from app.infrastructure.repositories.orden_repo_sqlalchemy import OrdenRepoSQLAlchemy
from app.infrastructure.repositories.orden_item_repo_sqlalchemy import OrdenItemRepoSQLAlchemy
from app.infrastructure.repositories.receta_repo_sqlalchemy import RecetaRepoSQLAlchemy
from app.infrastructure.repositories.inventario_repo_sqlalchemy import InventarioRepoSQLAlchemy
from app.infrastructure.repositories.ingrediente_repo_sqlalchemy import IngredienteRepoSQLAlchemy
from app.infrastructure.repositories.movimiento_inventario_repo_sqlalchemy import MovimientoInventarioRepoSQLAlchemy
from app.application.dtos.orden_dto import (
    CrearOrdenRequestDTO,
    CrearOrdenResponseDTO,
    ConfirmarOrdenResponseDTO,
    OrdenItemUpdateDTO,
    OrdenItemResponseDTO,
    OrdenItemDetalleDTO,
    OrdenDetalleResponseDTO,
)
from app.infrastructure.repositories.comanda_repo_sqlalchemy import ComandaRepoSQLAlchemy
from app.domain.exceptions.mesa_exceptions import MesaNoEncontradaException, MesaNoDisponibleException
from app.domain.exceptions.orden_exceptions import (
    OrdenNoConfirmableException,
    OrdenNoEncontradaException,
    OrdenNoModificableException,
)
from app.domain.exceptions.inventario_exceptions import StockInsuficienteException, StockInsuficienteOrdenException

orden_router = APIRouter(prefix="/ordenes", tags=["ordenes"])


def stock_insuficiente_detail(exc: StockInsuficienteException) -> dict:
    return {
        "error": "STOCK_INSUFICIENTE",
        "mensaje": str(exc),
        "ingrediente_id": exc.ingrediente_id,
        "disponible": float(exc.disponible),
        "requerido": float(exc.requerido),
    }


def stock_insuficiente_orden_detail(exc: StockInsuficienteOrdenException) -> dict:
    return {
        "error": "STOCK_INSUFICIENTE",
        "mensaje": str(exc),
        "detalles": exc.detalles,
    }


@orden_router.post(
    "/",
    summary="Crear o actualizar orden de mesa activa",
    response_model=CrearOrdenResponseDTO,
    status_code=201,
    description="Crea una orden para una mesa ocupada o agrega información a la orden abierta existente."
)
async def crear_orden(
    request: CrearOrdenRequestDTO,
    current_user: dict = Depends(get_current_pos_user),
    db: AsyncSession = Depends(get_db_session),
) -> CrearOrdenResponseDTO:
    """Endpoint RF-09: Crear o actualizar orden de mesa activa."""
    if current_user.get('rol') not in ['mesero', 'cajero', 'administrador']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo meseros, cajeros o administradores pueden crear órdenes."
        )

    rid = current_user["restaurante_id"]
    mesa_repo = MesaRepoSQLAlchemy(db, rid)
    orden_repo = OrdenRepoSQLAlchemy(db, rid)
    receta_repo = RecetaRepoSQLAlchemy(db, rid)
    inventario_repo = InventarioRepoSQLAlchemy(db)
    ingrediente_repo = IngredienteRepoSQLAlchemy(db, rid)
    use_case = CrearOrdenUC(mesa_repo, orden_repo, receta_repo, inventario_repo, ingrediente_repo)

    try:
        orden = await use_case.execute(
            mesa_id=request.mesa_id,
            mesero_id=current_user.get('id'),
            request=request,
        )

        return CrearOrdenResponseDTO(
            orden_id=orden.id,
            mesa_id=orden.mesa_id,
            mesero_id=orden.mesero_id,
            num_comensales=orden.num_comensales,
            estado=orden.estado.value,
            hora_apertura=orden.hora_apertura,
            total_neto=orden.total_neto,
            mensaje="Orden creada o actualizada exitosamente.",
        )

    except MesaNoEncontradaException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except MesaNoDisponibleException as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except StockInsuficienteException as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=stock_insuficiente_detail(exc),
        )
    except StockInsuficienteOrdenException as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=stock_insuficiente_orden_detail(exc),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la orden: {str(exc)}"
        )


@orden_router.get(
    "/{orden_id}",
    summary="Obtener detalles de una orden",
    response_model=OrdenDetalleResponseDTO,
    status_code=200,
    description="Recupera los detalles de una orden y sus ítems."
)
async def obtener_orden(
    orden_id: int,
    current_user: dict = Depends(get_current_pos_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrdenDetalleResponseDTO:
    if current_user.get('rol') not in ['mesero', 'cajero', 'administrador']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo meseros, cajeros o administradores pueden consultar órdenes."
        )

    rid = current_user["restaurante_id"]
    orden_repo = OrdenRepoSQLAlchemy(db, rid)
    receta_repo = RecetaRepoSQLAlchemy(db, rid)
    try:
        orden = await orden_repo.obtener_por_id(orden_id)
        if not orden:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Orden ID {orden_id} no existe")

        items = []
        for item in orden.items:
            receta = await receta_repo.obtener_por_id(item.receta_id)
            imagen_base64 = None
            if receta and receta.imagen:
                mime = receta.imagen_tipo or 'image/png'
                imagen_base64 = f"data:{mime};base64,{base64.b64encode(receta.imagen).decode()}"

            items.append(
                OrdenItemDetalleDTO(
                    id=item.id,
                    receta_id=item.receta_id,
                    cantidad=item.cantidad,
                    precio_unitario=item.precio_unitario,
                    estado=item.estado,
                    notas=item.observaciones,
                    image=imagen_base64,
                )
            )

        return OrdenDetalleResponseDTO(
            orden_id=orden.id,
            mesa_id=orden.mesa_id,
            mesero_id=orden.mesero_id,
            num_comensales=orden.num_comensales,
            estado=orden.estado.value,
            hora_apertura=orden.hora_apertura,
            notas_generales=orden.notas_generales,
            total_bruto=orden.total_bruto,
            total_neto=orden.total_neto,
            items=items,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener la orden: {str(exc)}"
        )


@orden_router.patch(
    "/{orden_id}/items/{item_id}",
    summary="Modificar cantidad o notas de un ítem de orden",
    response_model=OrdenItemResponseDTO,
    status_code=200,
    description="Modifica la cantidad o notas de un ítem mientras la orden está abierta."
)
async def modificar_item_orden(
    orden_id: int,
    item_id: int,
    request: OrdenItemUpdateDTO,
    current_user: dict = Depends(get_current_pos_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrdenItemResponseDTO:
    if current_user.get('rol') not in ['mesero', 'cajero', 'administrador']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo meseros, cajeros o administradores pueden modificar ítems."
        )

    rid = current_user["restaurante_id"]
    orden_repo = OrdenRepoSQLAlchemy(db, rid)
    orden_item_repo = OrdenItemRepoSQLAlchemy(db)
    receta_repo = RecetaRepoSQLAlchemy(db, rid)
    inventario_repo = InventarioRepoSQLAlchemy(db)
    use_case = ModificarOrdenItemUC(orden_repo, orden_item_repo, receta_repo, inventario_repo)
    try:
        item = await use_case.execute(
            orden_id=orden_id,
            orden_item_id=item_id,
            cantidad=request.cantidad,
            notas=request.notas,
        )
        return OrdenItemResponseDTO(
            id=item.id,
            receta_id=item.receta_id,
            cantidad=item.cantidad,
            precio_unitario=item.precio_unitario,
            notas=item.observaciones,
        )
    except OrdenNoEncontradaException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except OrdenNoModificableException as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al modificar el ítem: {str(exc)}"
        )


@orden_router.delete(
    "/{orden_id}/items/{item_id}",
    summary="Eliminar un ítem de una orden abierta",
    status_code=200,
    description="Elimina un ítem de la orden mientras la orden está abierta. Si no quedan ítems, cierra la orden y libera la mesa."
)
async def eliminar_item_orden(
    orden_id: int,
    item_id: int,
    current_user: dict = Depends(get_current_pos_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    if current_user.get('rol') not in ['mesero', 'cajero', 'administrador']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo meseros, cajeros o administradores pueden eliminar ítems."
        )

    rid = current_user["restaurante_id"]
    orden_repo = OrdenRepoSQLAlchemy(db, rid)
    orden_item_repo = OrdenItemRepoSQLAlchemy(db)
    use_case = EliminarOrdenItemUC(orden_repo, orden_item_repo)
    try:
        await use_case.execute(orden_id=orden_id, orden_item_id=item_id)
        
        # Verificar si quedan ítems en la orden
        orden = await orden_repo.obtener_por_id(orden_id)
        if orden and len(orden.items) == 0:
            # Si no hay ítems, cerrar orden y liberar mesa
            from sqlalchemy import select
            from app.infrastructure.database.models.mesa import OrdenORM, MesaORM
            from app.domain.enums.estado_orden import EstadoOrdenEnum
            from datetime import datetime
            
            orden_result = await db.execute(
                select(OrdenORM).where(OrdenORM.id == orden_id)
            )
            orden_orm = orden_result.scalar_one_or_none()
            
            if orden_orm:
                # Marcar la orden con un estado permitido por la base de datos.
                orden_orm.estado = EstadoOrdenEnum.PAGADA.value
                orden_orm.hora_cierre = datetime.utcnow()
                
                # Liberar la mesa
                mesa_result = await db.execute(
                    select(MesaORM).where(MesaORM.id == orden_orm.mesa_id)
                )
                mesa = mesa_result.scalar_one_or_none()
                
                if mesa:
                    mesa.estado = "libre"
                    mesa.comensales_actuales = 0
        
        await db.commit()
        return {"mensaje": "Ítem eliminado de la orden exitosamente."}
    except OrdenNoEncontradaException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except OrdenNoModificableException as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el ítem: {str(exc)}"
        )


@orden_router.post(
    "/{orden_id}/confirmar",
    summary="Confirmar orden abierta",
    response_model=ConfirmarOrdenResponseDTO,
    status_code=200,
    description="Confirma una orden abierta y marca la orden como en preparación."
)
async def confirmar_orden(
    orden_id: int,
    current_user: dict = Depends(get_current_pos_user),
    db: AsyncSession = Depends(get_db_session),
) -> ConfirmarOrdenResponseDTO:
    if current_user.get('rol') not in ['mesero', 'cajero', 'administrador']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo meseros, cajeros o administradores pueden confirmar órdenes."
        )

    rid = current_user["restaurante_id"]
    orden_repo = OrdenRepoSQLAlchemy(db, rid)
    orden_item_repo = OrdenItemRepoSQLAlchemy(db)
    receta_repo = RecetaRepoSQLAlchemy(db, rid)
    inventario_repo = InventarioRepoSQLAlchemy(db)
    ingrediente_repo = IngredienteRepoSQLAlchemy(db, rid)
    movimiento_repo = MovimientoInventarioRepoSQLAlchemy(db)
    comanda_repo = ComandaRepoSQLAlchemy(db)
    use_case = ConfirmarOrdenUC(
        orden_repo,
        orden_item_repo,
        receta_repo,
        inventario_repo,
        ingrediente_repo,
        movimiento_repo,
        comanda_repo,
    )

    try:
        orden, ticket = await use_case.execute(orden_id=orden_id, usuario_id=current_user.get('id'))

        return ConfirmarOrdenResponseDTO(
            orden_id=orden.id,
            estado=orden.estado.value,
            hora_confirmacion=orden.hora_confirmacion,
            num_comensales=orden.num_comensales,
            comanda_ticket=ticket,
            mensaje="Orden confirmada exitosamente. Comanda lista para imprimir.",
        )

    except OrdenNoEncontradaException as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except OrdenNoConfirmableException as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "ORDEN_NO_CONFIRMABLE", "mensaje": str(exc)}
        )
    except StockInsuficienteException as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=stock_insuficiente_detail(exc),
        )
    except StockInsuficienteOrdenException as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=stock_insuficiente_orden_detail(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al confirmar la orden: {str(exc)}"
        )


@orden_router.post(
    "/{orden_id}/validar-cierre",
    summary="Validar cierre de orden al volver a mesas",
    status_code=200,
    description="Verifica si la orden está vacía y libera la mesa si es necesario"
)
async def validar_cierre_orden(
    orden_id: int,
    current_user: dict = Depends(get_current_pos_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Endpoint para validar si debe cerrarse la orden al volver a mesas"""
    if current_user.get('rol') not in ['mesero', 'cajero', 'administrador']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado"
        )
    
    try:
        from sqlalchemy import select
        from app.infrastructure.database.models.mesa import OrdenORM, MesaORM
        from app.domain.enums.estado_orden import EstadoOrdenEnum
        from datetime import datetime
        
        # Obtener la orden
        orden_result = await db.execute(
            select(OrdenORM).where(OrdenORM.id == orden_id)
        )
        orden_orm = orden_result.scalar_one_or_none()
        
        if not orden_orm:
            raise ValueError("Orden no encontrada")
        
        # Si la orden está vacía (sin items o con total = 0) y está abierta
        if orden_orm.total_neto == 0 and orden_orm.estado == EstadoOrdenEnum.ABIERTA.value:
            # Cerrar orden con un estado permitido por la base de datos.
            orden_orm.estado = EstadoOrdenEnum.PAGADA.value
            orden_orm.hora_cierre = datetime.utcnow()
            
            # Liberar mesa
            mesa_result = await db.execute(
                select(MesaORM).where(MesaORM.id == orden_orm.mesa_id)
            )
            mesa = mesa_result.scalar_one_or_none()
            
            if mesa:
                mesa.estado = "libre"
                mesa.comensales_actuales = 0
            
            await db.commit()
            return {
                "mensaje": "Orden cerrada y mesa liberada",
                "orden_id": orden_id,
                "mesa_liberada": True
            }
        
        await db.commit()
        return {
            "mensaje": "Orden aún tiene items",
            "orden_id": orden_id,
            "mesa_liberada": False
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al validar cierre: {str(e)}"
        )
