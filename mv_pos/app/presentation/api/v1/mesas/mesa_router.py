from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Path
from typing import Optional
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.presentation.dependencies.db_deps import get_db_session
from app.presentation.dependencies.auth_deps import get_current_user
from app.domain.use_cases.obtener_mesas_uc import (
    ObtenerEstadoMesasUC, 
    ObtenerMapaMesasUC,
    ObtenerEstadoMesaUC
)
from app.domain.use_cases.abrir_mesa_uc import AbrirMesaUC
from app.domain.use_cases.reservar_mesa_uc import ReservarMesaUC, ReservarMesasUC
from app.infrastructure.repositories.mesa_repo_sqlalchemy import MesaRepoSQLAlchemy
from app.infrastructure.repositories.orden_repo_sqlalchemy import OrdenRepoSQLAlchemy
from app.infrastructure.repositories.usuario_repo_sqlalchemy import UsuarioRepoSQLAlchemy
from app.infrastructure.repositories.reserva_repo_sqlalchemy import ReservaRepoSQLAlchemy
from app.application.dtos.mesa_dto import (
    MesaStatusDTO, 
    MesaMapResponseDTO, 
    MesaListResponseDTO,
    AbrirMesaRequestDTO,
    AbrirMesaResponseDTO,
    ReservarMesaRequestDTO,
    ReservarMesaResponseDTO,
    ReservarMesasRequestDTO,
    ReservarMesasResponseDTO,
)
from app.domain.exceptions.mesa_exceptions import (
    MesaNoEncontradaException,
    MesaNoDisponibleException,
    CapacidadMesaExcedidaException,
    ReservaMesaException,
)


mesa_router = APIRouter(prefix="/mesas", tags=["mesas"])


@mesa_router.get(
    "/",
    summary="Listar todas las mesas con estado en tiempo real (RF-05)",
    response_model=MesaListResponseDTO,
    description="Obtiene lista de todas las mesas activas con su estado actual desde v_mesas_estado. Actualización < 3s."
)
async def listar_mesas(
    zona: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
) -> MesaListResponseDTO:
    """
    **Endpoint RF-05: Lista todas las mesas con estado en tiempo real**
    
    - Estados: libre, ocupada, reservada, en_espera_cuenta
    - Si hay orden activa, incluye: mesero, comensales, total_neto
    - Responde en < 1s para garantizar actualización < 3s con polling cada 2s
    - Parámetro opcional `zona` para filtrar por zona
    """
    mesa_repo = MesaRepoSQLAlchemy(db)
    use_case = ObtenerEstadoMesasUC(mesa_repo)
    
    mesas = await use_case.execute(zona=zona)
    
    return MesaListResponseDTO(
        mesas=mesas,
        total=len(mesas),
        timestamp=datetime.utcnow()
    )


@mesa_router.get(
    "/mapa/visual",
    summary="Obtener mapa visual de mesas agrupado por zona (RF-05)",
    response_model=MesaMapResponseDTO,
    description="Retorna mapa de mesas agrupadas por zona con estadísticas. Optimizado para UI."
)
async def obtener_mapa_visual(
    zona: Optional[str] = None,
    db: AsyncSession = Depends(get_db_session)
) -> MesaMapResponseDTO:
    """
    **Endpoint RF-05: Mapa visual de mesas agrupado por zona**
    
    Retorna:
    - `mapa`: Diccionario {zona: [mesas]} para renderizar en grid
    - `total_mesas`: Total de mesas activas
    - `ocupadas`, `reservadas`, `libres`: Contadores por estado
    - `timestamp`: Hora de la consulta (para validar actualización)
    
    **SLA:** Responde en < 1s para garantizar actualización < 3s con polling cliente cada 2s
    
    Colores sugeridos para UI:
    - `libre`: Verde (#4CAF50)
    - `ocupada`: Rojo (#F44336)
    - `reservada`: Azul (#2196F3)
    - `en_espera_cuenta`: Naranja (#FF9800)
    """
    mesa_repo = MesaRepoSQLAlchemy(db)
    use_case = ObtenerMapaMesasUC(mesa_repo)
    
    return await use_case.execute(zona=zona)


@mesa_router.get(
    "/{mesa_id}",
    summary="Obtener estado de una mesa específica (RF-05)",
    response_model=MesaStatusDTO,
    description="Obtiene estado en tiempo real de una mesa específica."
)
async def obtener_mesa_estado(
    mesa_id: int,
    db: AsyncSession = Depends(get_db_session)
) -> MesaStatusDTO:
    """
    **Endpoint RF-05: Estado de mesa específica**
    
    Retorna estado actual (libre, ocupada, reservada, en_espera_cuenta)
    con detalles de orden si la mesa está ocupada.
    """
    mesa_repo = MesaRepoSQLAlchemy(db)
    use_case = ObtenerEstadoMesaUC(mesa_repo)
    
    mesa = await use_case.execute(mesa_id=mesa_id)
    
    if not mesa:
        raise HTTPException(status_code=404, detail=f"Mesa {mesa_id} no encontrada")
    
    return mesa


@mesa_router.post(
    "/{mesa_id}/abrir",
    summary="Abrir una mesa (RF-06)",
    response_model=AbrirMesaResponseDTO,
    status_code=201,
    description="Abre una mesa registrando mesero y número de comensales. Crea orden automáticamente."
)
async def abrir_mesa(
    mesa_id: int = Path(..., gt=0, description="ID de la mesa a abrir"),
    request: AbrirMesaRequestDTO = ...,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
) -> AbrirMesaResponseDTO:
    """
    **Endpoint RF-06: Abrir una mesa**
    
    Abre una mesa para tomar orden:
    - Solo meseros pueden abrir mesas
    - Mesa debe estar en estado 'libre'
    - Registra hora, mesero y número de comensales
    - Crea orden automáticamente
    - Cambia estado mesa a 'ocupada'
    
    **Validaciones:**
    - Mesa debe existir y estar activa
    - num_comensales > 0
    - num_comensales <= capacidad mesa
    - Usuario debe tener rol 'mesero'
    
    **Response:**
    - orden_id: ID de la orden creada
    - hora_apertura: Timestamp de apertura
    - estado_mesa: 'ocupada'
    """
    
    # Validar rol (mesero, cajero o administrador)
    if current_user.get('rol') not in ['mesero', 'cajero', 'administrador']:
        raise HTTPException(
            status_code=403,
            detail="Solo meseros, cajeros o administradores pueden abrir mesas"
        )
    
    # Validar entrada
    if request.num_comensales <= 0:
        raise HTTPException(
            status_code=400, 
            detail="Número de comensales debe ser mayor a 0"
        )
    
    # Instanciar repositorios
    mesa_repo = MesaRepoSQLAlchemy(db)
    orden_repo = OrdenRepoSQLAlchemy(db)
    
    # Ejecutar use case
    use_case = AbrirMesaUC(mesa_repo, orden_repo)
    
    try:
        resultado = await use_case.execute(
            mesa_id=mesa_id,
            mesero_id=current_user.get('id'),
            mesero_nombre=current_user.get('nombre_completo'),
            request=request
        )
        return resultado
    
    except MesaNoEncontradaException as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    except MesaNoDisponibleException as e:
        raise HTTPException(status_code=409, detail=str(e))
    
    except CapacidadMesaExcedidaException as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al abrir mesa: {str(e)}")


@mesa_router.post(
    "/{mesa_id}/reservar",
    summary="Reservar una mesa",
    status_code=201,
    response_model=ReservarMesaResponseDTO,
    description="Crea una reserva para una mesa libre y marca la mesa como reservada."
)
async def reservar_mesa(
    mesa_id: int = Path(..., gt=0, description="ID de la mesa a reservar"),
    request: ReservarMesaRequestDTO = ...,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Endpoint RF-08: Reservar una mesa."""
    if current_user.get('rol') not in ['mesero', 'administrador']:
        raise HTTPException(
            status_code=403,
            detail="Solo meseros o administradores pueden reservar mesas"
        )

    try:
        mesa_repo = MesaRepoSQLAlchemy(db)
        reserva_repo = ReservaRepoSQLAlchemy(db)
        use_case = ReservarMesaUC(mesa_repo, reserva_repo)

        resultado = await use_case.execute(
            mesa_id=mesa_id,
            usuario_id=current_user.get('id'),
            request=request
        )

        return resultado
    except MesaNoEncontradaException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ReservaMesaException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except MesaNoDisponibleException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except CapacidadMesaExcedidaException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al reservar mesa: {str(e)}")


@mesa_router.post(
    "/reservar",
    summary="Reservar una o varias mesas",
    status_code=201,
    response_model=ReservarMesasResponseDTO,
    description="Crea reservas para una o varias mesas libres y marca cada mesa como reservada."
)
async def reservar_mesas(
    request: ReservarMesasRequestDTO = ...,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Endpoint RF-08: Reservar una o varias mesas."""
    if current_user.get('rol') not in ['mesero', 'administrador']:
        raise HTTPException(
            status_code=403,
            detail="Solo meseros o administradores pueden reservar mesas"
        )

    try:
        mesa_repo = MesaRepoSQLAlchemy(db)
        reserva_repo = ReservaRepoSQLAlchemy(db)
        use_case = ReservarMesasUC(mesa_repo, reserva_repo)

        resultado = await use_case.execute(
            mesa_ids=request.mesa_ids,
            usuario_id=current_user.get('id'),
            request=request
        )

        return resultado
    except MesaNoEncontradaException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ReservaMesaException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except MesaNoDisponibleException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except CapacidadMesaExcedidaException as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al reservar mesas: {str(e)}")


@mesa_router.post(
    "/{mesa_id}/transferir",
    summary="Transferir mesa a otro mesero",
    status_code=200,
    description="Transfiere una mesa a otro mesero. Solo para órdenes activas."
)
async def transferir_mesa(
    mesa_id: int = Path(..., gt=0, description="ID de la mesa a transferir"),
    request_data: dict = ...,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    **Endpoint: Transferir mesa a otro mesero**
    
    Transfiere una mesa (orden activa) a otro mesero:
    - Solo meseros pueden transferir mesas
    - Orden debe estar activa (no pagada ni cancelada)
    - Nuevo mesero debe existir, estar activo y ser mesero
    
    **Request body:**
    ```json
    {
      "nuevo_mesero_id": 5
    }
    ```
    
    **Response:**
    - orden_id: ID de la orden transferida
    - mesero_anterior_nombre: Quién tenía la mesa
    - mesero_nuevo_nombre: Quién la recibe
    - hora_transferencia: Timestamp
    """
    from app.domain.use_cases.transferir_mesa_uc import TransferirMesaUC
    from app.application.dtos.transferencia_union_dto import TransferirMesaRequestDTO
    from app.domain.exceptions.orden_exceptions import TransferenciaMesaException
    from app.infrastructure.repositories.usuario_repo_sqlalchemy import UsuarioRepoSQLAlchemy
    
    # Validar rol
    if current_user.get('rol') != 'mesero':
        raise HTTPException(
            status_code=403,
            detail="Solo meseros pueden transferir mesas"
        )
    
    try:
        # Obtener orden activa de la mesa
        orden_repo = OrdenRepoSQLAlchemy(db)
        orden = await orden_repo.obtener_orden_activa_por_mesa(mesa_id)
        
        if not orden:
            raise HTTPException(
                status_code=404,
                detail=f"No existe orden activa en mesa {mesa_id}"
            )
        
        # Ejecutar use case
        usuario_repo = UsuarioRepoSQLAlchemy(db)
        use_case = TransferirMesaUC(orden_repo, usuario_repo)
        
        dto_request = TransferirMesaRequestDTO(
            nuevo_mesero_id=request_data.get('nuevo_mesero_id')
        )
        
        resultado = await use_case.execute(
            orden_id=orden.id,
            mesero_id_anterior=orden.mesero_id,
            mesero_nombre_anterior=current_user.get('nombre_completo'),
            nuevo_mesero_id=request_data.get('nuevo_mesero_id'),
            request=dto_request
        )
        
        return {
            "status": "success",
            "data": {
                "orden_id": resultado.orden_id,
                "mesa_id": resultado.mesa_id,
                "mesa_numero": resultado.mesa_numero,
                "mesero_anterior": {
                    "id": resultado.mesero_id_anterior,
                    "nombre": resultado.mesero_anterior_nombre
                },
                "mesero_nuevo": {
                    "id": resultado.mesero_id_nuevo,
                    "nombre": resultado.mesero_nuevo_nombre
                },
                "hora_transferencia": resultado.hora_transferencia,
                "mensaje": resultado.mensaje
            }
        }
    
    except TransferenciaMesaException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al transferir mesa: {str(e)}")


@mesa_router.post(
    "/unir",
    summary="Unir dos mesas o mover una orden a una mesa libre",
    status_code=200,
    description="Consolida dos mesas ocupadas en una sola orden, o traslada una orden ocupada a una mesa libre."
)
async def unir_mesas(
    request_data: dict = ...,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    **Endpoint: Unir dos mesas**
    
    Une dos mesas ocupadas en una sola orden, o traslada una orden ocupada a una mesa libre:
    - Mesa origen debe estar ocupada y activa
    - Mesa destino puede estar ocupada o libre
    - Si destino está ocupada, copia ítems de origen a destino
    - Si destino está libre, traslada la orden completa
    - Libera mesa origen
    
    **Request body:**
    ```json
    {
      "mesa_origen_id": 1,
      "mesa_destino_id": 2
    }
    ```
    
    **Response:**
    - orden_destino_id: Orden que recibe los ítems
    - num_items_consolidados: Cantidad de ítems copiados
    - nuevo_total_comensales: Suma de comensales
    """
    from app.domain.use_cases.unir_mesas_uc import UnirMesasUC
    from app.application.dtos.transferencia_union_dto import UnirMesasRequestDTO
    from app.domain.exceptions.orden_exceptions import UnionMesasException
    
    # Validar rol (solo mesero o admin)
    if current_user.get('rol') not in ['mesero', 'administrador']:
        raise HTTPException(
            status_code=403,
            detail="Solo meseros pueden unir mesas"
        )
    
    try:
        # Instanciar repositorios
        orden_repo = OrdenRepoSQLAlchemy(db)
        mesa_repo = MesaRepoSQLAlchemy(db)
        
        # Ejecutar use case
        use_case = UnirMesasUC(orden_repo, mesa_repo)
        
        dto_request = UnirMesasRequestDTO(
            mesa_origen_id=request_data.get('mesa_origen_id'),
            mesa_destino_id=request_data.get('mesa_destino_id')
        )
        
        resultado = await use_case.execute(request=dto_request)
        
        return {
            "status": "success",
            "data": {
                "orden_destino_id": resultado.orden_destino_id,
                "mesa_destino": {
                    "id": resultado.mesa_destino_id,
                    "numero": resultado.mesa_destino_numero
                },
                "mesa_origen": {
                    "id": resultado.mesa_origen_id,
                    "numero": resultado.mesa_origen_numero
                },
                "num_items_consolidados": resultado.num_items_consolidados,
                "nuevo_total_comensales": resultado.nuevo_total_comensales,
                "hora_union": resultado.hora_union,
                "mensaje": resultado.mensaje
            }
        }
    
    except UnionMesasException as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al unir mesas: {str(e)}")

