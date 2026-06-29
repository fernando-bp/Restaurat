from __future__ import annotations
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.presentation.schemas.cierre_caja import (
    CierreCajaResumenDTO,
    CierreCajaRequestDTO,
    CierreCajaResponseDTO,
    ResumenPagoDTO,
)
from app.presentation.dependencies.auth_deps import get_current_user
from app.presentation.dependencies.db_deps import get_db_session
from app.domain.use_cases.cierre_caja_uc import CierreCajaUseCase
from app.infrastructure.repositories.usuario_repo_sqlalchemy import UsuarioRepoSQLAlchemy

cierre_caja_router = APIRouter(prefix="/cierre-caja", tags=["cierre-caja"])


@cierre_caja_router.get(
    "/validar-mesas",
    summary="Validar estado de mesas",
    description="Verifica si todas las mesas están cerradas para permitir cierre de caja",
)
async def validar_mesas_cerradas(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    """Valida si es posible realizar el cierre de caja.
    
    Response:
    ```json
    {
      "todas_cerradas": true,
      "mesas_abiertas": null,
      "cantidad_mesas_abiertas": 0,
      "mensaje": "Todas las mesas están cerradas. Puedes proceder con el cierre."
    }
    ```
    
    O si hay mesas abiertas:
    ```json
    {
      "todas_cerradas": false,
      "mesas_abiertas": [2, 5, 7],
      "cantidad_mesas_abiertas": 3,
      "mensaje": "Hay 3 mesa(s) aún abiertas. Ciérrales antes de proceder."
    }
    ```
    """
    
    # Validar permisos
    if current_user.get('rol') not in ('administrador', 'admin', 'cajero'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado"
        )
    
    usuario_repo = UsuarioRepoSQLAlchemy(db)
    use_case = CierreCajaUseCase(db, usuario_repo)
    
    todas_cerradas, mesas_abiertas = await use_case.verificar_mesas_cerradas()
    
    return {
        "todas_cerradas": todas_cerradas,
        "mesas_abiertas": mesas_abiertas,
        "cantidad_mesas_abiertas": len(mesas_abiertas) if mesas_abiertas else 0,
        "mensaje": (
            "✓ Todas las mesas están cerradas. Puedes proceder con el cierre de caja."
            if todas_cerradas
            else f"✗ Hay {len(mesas_abiertas)} mesa(s) aún abiertas: {mesas_abiertas}. Ciérrales antes de proceder."
        )
    }


@cierre_caja_router.get(
    "/resumen",
    response_model=CierreCajaResumenDTO,
    summary="Obtener resumen de caja antes del cierre",
    description="Devuelve el resumen de ingresos por forma de pago del día",
)
async def obtener_resumen_caja(
    fecha: date = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CierreCajaResumenDTO:
    """Obtiene el resumen de caja antes de contar efectivo.
    
    Solo autorizado para: administrador, cajero
    """
    
    # Validar permisos
    if current_user.get('rol') not in ('administrador', 'admin', 'cajero'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para ver cierre de caja"
        )
    
    # Si no se proporciona fecha, usar hoy
    if fecha is None:
        fecha = date.today()
    
    usuario_repo = UsuarioRepoSQLAlchemy(db)
    use_case = CierreCajaUseCase(db, usuario_repo)
    
    resumen = await use_case.obtener_resumen_caja(fecha, reiniciar_si_cerrado=True)
    
    # Convertir a DTO
    por_forma_pago = [
        ResumenPagoDTO(
            forma_pago=item['forma_pago'],
            total=item['total'],
            cantidad_transacciones=item['cantidad']
        )
        for item in resumen['por_forma_pago']
    ]
    
    return CierreCajaResumenDTO(
        fecha=resumen['fecha'],
        total_ventas=resumen['total_ventas'],
        por_forma_pago=por_forma_pago,
        total_efectivo_sistema=resumen['total_efectivo_sistema'],
        total_tarjeta_debito=resumen['total_tarjeta_debito'],
        total_tarjeta_credito=resumen['total_tarjeta_credito'],
        total_transferencia=resumen['total_transferencia'],
        total_cortesia=resumen['total_cortesia'],
        total_descuentos=resumen['total_descuentos'],
    )


@cierre_caja_router.post(
    "/ejecutar",
    response_model=CierreCajaResponseDTO,
    summary="Ejecutar cierre de caja",
    description="Cierra la caja del día con conteo de efectivo físico y valida cuadre",
)
async def ejecutar_cierre_caja(
    payload: CierreCajaRequestDTO,
    fecha: date = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CierreCajaResponseDTO:
    """Ejecuta el cierre de caja.
    
    ⚠️ VALIDACIÓN IMPORTANTE: Solo se permite cerrar caja si TODAS las mesas están cerradas.
    
    Pasos:
    1. ✓ Verifica que todas las mesas estén cerradas
    2. Calcula total efectivo contado desde billetes y monedas
    3. Compara con total del sistema
    4. Crea registro de cierre con diferencia
    5. Retorna resultado con validación
    
    Solo autorizado para: administrador, cajero
    """
    
    # Validar permisos
    if current_user.get('rol') not in ('administrador', 'admin', 'cajero'):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No autorizado para ejecutar cierre de caja"
        )
    
    # Si no se proporciona fecha, usar hoy
    if fecha is None:
        fecha = date.today()
    
    # VALIDACIÓN CRÍTICA: Verificar que todas las mesas estén cerradas
    usuario_repo = UsuarioRepoSQLAlchemy(db)
    use_case = CierreCajaUseCase(db, usuario_repo)
    
    todas_cerradas, mesas_abiertas = await use_case.verificar_mesas_cerradas()
    
    if not todas_cerradas:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"No se puede cerrar caja. Hay {len(mesas_abiertas)} mesa(s) aún abiertas: {mesas_abiertas}. Cierre todas las mesas antes de proceder."
        )
    
    # Calcular total efectivo contado
    total_efectivo_contado = payload.efectivo_contado.calcular_total()
    
    # Ejecutar use case
    try:
        resumen = await use_case.obtener_resumen_caja(fecha)
        cierre = await use_case.ejecutar_cierre(
            fecha=fecha,
            total_efectivo_contado=total_efectivo_contado,
            cajero_id=current_user['id'],
            observaciones=payload.observaciones,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    
    # Calcular diferencia porcentaje
    diferencia_porcentaje = None
    if cierre.total_efectivo_sistema > 0:
        diferencia_porcentaje = (cierre.diferencia_efectivo / cierre.total_efectivo_sistema) * 100
    
    # Determinar si cuadra (tolerancia de ±100)
    cuadra = abs(cierre.diferencia_efectivo) <= 100
    
    return CierreCajaResponseDTO(
        id=cierre.id,
        fecha=str(cierre.fecha),
        total_efectivo_sistema=float(cierre.total_efectivo_sistema),
        total_efectivo_contado=float(cierre.total_efectivo_contado),
        total_tarjeta_debito=resumen['total_tarjeta_debito'],
        total_tarjeta_credito=resumen['total_tarjeta_credito'],
        total_transferencia=resumen['total_transferencia'],
        total_cortesia=resumen['total_cortesia'],
        total_descuentos=resumen['total_descuentos'],
        total_ventas=resumen['total_ventas'],
        diferencia_efectivo=float(cierre.diferencia_efectivo),
        diferencia_porcentaje=diferencia_porcentaje,
        cuadra=cuadra,
        observaciones=cierre.observaciones,
        created_at=cierre.created_at,
    )
