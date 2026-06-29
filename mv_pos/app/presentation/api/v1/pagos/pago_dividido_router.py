from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from app.application.dtos.pago_dividido_dto import (
    CrearPagoDivididoRequest,
    PagoDivididoResumenDTO,
    RegistrarPagoPersonaRequest,
    RegistrarPagoPersonaResponse,
)
from app.application.use_cases.pagos.pago_dividido_uc import CrearPagoDivididoUC, ObtenerResumenPagoDivididoUC
from app.application.use_cases.pagos.registrar_pago_persona_dividido_uc import RegistrarPagoPersonaDividoUC
from app.infrastructure.database.models.pago_dividido import PagoDivididoORM
from app.infrastructure.database.models.mesa import OrdenORM, MesaORM
from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.enums.estado_mesa import EstadoMesaEnum
from app.presentation.dependencies.auth_deps import get_current_user
from app.presentation.dependencies.db_deps import get_db_session

pago_dividido_router = APIRouter(prefix="/pagos-divididos", tags=["pagos-divididos"])


@pago_dividido_router.post(
    "/crear",
    summary="Crear una división de pago",
    response_model=PagoDivididoResumenDTO,
    status_code=201,
    description="Divide una cuenta entre N personas equitativamente"
)
async def crear_pago_dividido(
    request: CrearPagoDivididoRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PagoDivididoResumenDTO:
    """
    Crea una división de pago para una orden.
    
    Divide el monto total equitativamente entre el número de personas especificado.
    Cada persona recibirá el mismo monto a pagar.
    
    Requisitos:
    - numero_personas >= 2
    - monto_total > 0
    """
    if current_user.get('rol') not in ('mesero', 'cajero', 'administrador'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
    
    try:
        use_case = CrearPagoDivididoUC(db)
        resultado = await use_case.ejecutar(
            orden_id=request.orden_id,
            numero_personas=request.numero_personas,
            monto_total=request.monto_total,
            montos_personas=request.montos_personas
        )
        await db.commit()
        return resultado
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear pago dividido: {str(e)}"
        )


@pago_dividido_router.get(
    "/{pago_dividido_id}",
    summary="Obtener resumen de pago dividido",
    response_model=PagoDivididoResumenDTO,
    status_code=200,
    description="Obtiene el estado actual de una división de pago"
)
async def obtener_resumen_pago_dividido(
    pago_dividido_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PagoDivididoResumenDTO:
    """Obtiene el resumen de un pago dividido"""
    if current_user.get('rol') not in ('mesero', 'cajero', 'administrador'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
    
    try:
        use_case = ObtenerResumenPagoDivididoUC(db)
        return await use_case.ejecutar(pago_dividido_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener resumen: {str(e)}"
        )


@pago_dividido_router.post(
    "/{pago_dividido_id}/pagar",
    summary="Registrar pago de una persona",
    response_model=RegistrarPagoPersonaResponse,
    status_code=200,
    description="Registra el pago de una persona dentro de una división"
)
async def registrar_pago_persona(
    pago_dividido_id: int,
    request: RegistrarPagoPersonaRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> RegistrarPagoPersonaResponse:
    """
    Registra el pago de una persona en una división.
    
    Valida que:
    - La forma de pago sea válida
    - Se proporcionen los datos necesarios (efectivo, tarjeta, transferencia)
    - La persona no haya pagado ya
    - El pago dividido no esté completado
    
    Ejemplos de uso:
    
    **Pago en efectivo:**
    ```json
    {
        "pago_dividido_id": 1,
        "numero_persona": 1,
        "forma_pago": "efectivo",
        "monto_recibido": 20000
    }
    ```
    
    **Pago con tarjeta:**
    ```json
    {
        "pago_dividido_id": 1,
        "numero_persona": 2,
        "forma_pago": "tarjeta_debito",
        "referencia_datafono": "TRANS123456"
    }
    ```
    
    **Pago por transferencia:**
    ```json
    {
        "pago_dividido_id": 1,
        "numero_persona": 3,
        "forma_pago": "nequi",
        "numero_comprobante": "NEQUI987654"
    }
    ```
    """
    if current_user.get('rol') not in ('mesero', 'cajero', 'administrador'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")
    
    try:
        # Obtener pago dividido y orden para poder liberar mesa después
        pago_div_result = await db.execute(
            select(PagoDivididoORM).where(PagoDivididoORM.id == pago_dividido_id)
        )
        pago_dividido = pago_div_result.scalar_one_or_none()
        if not pago_dividido:
            raise ValueError(f"Pago dividido {pago_dividido_id} no encontrado")
        orden_id = pago_dividido.orden_id
        
        # Registrar pago de la persona
        use_case = RegistrarPagoPersonaDividoUC(db)
        resultado = await use_case.ejecutar(
            pago_dividido_id=pago_dividido_id,
            numero_persona=request.numero_persona,
            forma_pago=request.forma_pago,
            cajero_id=current_user.get('id'),
            monto_recibido=request.monto_recibido,
            referencia_datafono=request.referencia_datafono,
            numero_comprobante=request.numero_comprobante
        )
        # Si se completó la división, eliminar orden y liberar mesa
        if resultado.completado_division:
            # Obtener la orden
            orden_result = await db.execute(
                select(OrdenORM).where(OrdenORM.id == orden_id)
            )
            orden = orden_result.scalar_one_or_none()
            
            if orden:
                orden.estado = EstadoOrdenEnum.PAGADA.value
                orden.hora_cierre = datetime.utcnow()

                # Liberar la mesa
                mesa_result = await db.execute(
                    select(MesaORM).where(MesaORM.id == orden.mesa_id)
                )
                mesa = mesa_result.scalar_one_or_none()
                
                if mesa:
                    mesa.estado = EstadoMesaEnum.LIBRE.value
                
                # Guardar cierre de orden y liberacion de mesa
                await db.flush()
        
        await db.commit()
        return resultado
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al registrar pago: {str(e)}"
        )
