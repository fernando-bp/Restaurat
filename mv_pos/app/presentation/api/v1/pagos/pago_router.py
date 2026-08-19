from __future__ import annotations
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dtos.pago_dto import (
    PagoRequestDTO,
    PagoResponseDTO,
    PagoMixtoRequestDTO,
    CuentaDetalladaResponseDTO,
    CierreCajaRequestDTO,
    CierreCajaResponseDTO,
    DescuentoRequestDTO,
)
from app.application.use_cases.pagos.obtener_cuenta_detallada import ObtenerCuentaDetalladaUC
from app.application.use_cases.pagos.registrar_pago_efectivo import RegistrarPagoEfectivoUseCase
from app.application.use_cases.pagos.registrar_pago_tarjeta_transferencia import (
    RegistrarPagoTarjetaUseCase,
    RegistrarPagoTransferenciaUseCase,
)
from app.application.use_cases.pagos.registrar_pago_mixto import RegistrarPagoMixtoUC
from app.application.use_cases.pagos.aplicar_descuento import AplicarDescuentoUC
from app.application.use_cases.pagos.cierre_caja import RegistrarCierreCajaUC
from app.infrastructure.repositories.orden_repo_sqlalchemy import OrdenRepoSQLAlchemy
from app.infrastructure.repositories.mesa_repo_sqlalchemy import MesaRepoSQLAlchemy
from app.infrastructure.repositories.pago_repo_sqlalchemy import PagoRepoSQLAlchemy
from app.infrastructure.repositories.descuento_repo_sqlalchemy import DescuentoRepoSQLAlchemy
from app.presentation.dependencies.auth_deps import get_current_user
from app.presentation.dependencies.db_deps import get_db_session

pago_router = APIRouter(prefix="/pagos", tags=["pagos"])


@pago_router.get(
    "/cuenta/{orden_id}",
    summary="Obtener cuenta detallada de la orden",
    response_model=CuentaDetalladaResponseDTO,
    status_code=200,
    description="Genera la cuenta con ítems, descuentos, IVA y total a pagar."
)
async def obtener_cuenta_detallada(
    orden_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CuentaDetalladaResponseDTO:
    if current_user.get('rol') not in ('mesero', 'cajero', 'administrador'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    rid = current_user["restaurante_id"]
    orden_repo = OrdenRepoSQLAlchemy(db, rid)
    descuento_repo = DescuentoRepoSQLAlchemy(db)
    mesa_repo = MesaRepoSQLAlchemy(db, rid)
    use_case = ObtenerCuentaDetalladaUC(orden_repo, descuento_repo)

    try:
        cuenta = await use_case.ejecutar(orden_id)
        mesa = await mesa_repo.obtener_por_id(cuenta['mesa_id'])
        cuenta['mesa_numero'] = mesa.numero if mesa else 'N/A'
        return CuentaDetalladaResponseDTO(**cuenta)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@pago_router.post(
    "/efectivo",
    summary="Registrar pago en efectivo",
    response_model=PagoResponseDTO,
    status_code=201,
    description="Registra un pago en efectivo y calcula cambio automáticamente."
)
async def registrar_pago_efectivo(
    request: PagoRequestDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PagoResponseDTO:
    if current_user.get('rol') not in ('mesero', 'cajero', 'administrador'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para registrar pagos.")

    rid = current_user["restaurante_id"]
    orden_repo = OrdenRepoSQLAlchemy(db, rid)
    pago_repo = PagoRepoSQLAlchemy(db)
    mesa_repo = MesaRepoSQLAlchemy(db, rid)
    use_case = RegistrarPagoEfectivoUseCase(orden_repo, pago_repo, mesa_repo)

    try:
        resultado = await use_case.ejecutar(
            orden_id=request.orden_id,
            monto_adeudado=request.monto,
            monto_recibido=request.monto_recibido or Decimal('0'),
            cajero_id=current_user.get('id'),
        )
        return PagoResponseDTO(
            id=resultado['pago_id'],
            orden_id=request.orden_id,
            forma_pago='efectivo',
            monto=resultado['monto_pagado'],
            monto_recibido=resultado['monto_recibido'],
            cambio_entregado=resultado['cambio'],
            referencia_datafono=None,
            numero_comprobante=None,
            cajero_id=current_user.get('id'),
            created_at=datetime.utcnow(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@pago_router.post(
    "/tarjeta",
    summary="Registrar pago con tarjeta",
    response_model=PagoResponseDTO,
    status_code=201,
    description="Registra un pago con tarjeta de débito o crédito con referencia de datafono."
)
async def registrar_pago_tarjeta(
    request: PagoRequestDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PagoResponseDTO:
    if current_user.get('rol') not in ('mesero', 'cajero', 'administrador'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para registrar pagos.")

    rid = current_user["restaurante_id"]
    orden_repo = OrdenRepoSQLAlchemy(db, rid)
    pago_repo = PagoRepoSQLAlchemy(db)
    mesa_repo = MesaRepoSQLAlchemy(db, rid)
    use_case = RegistrarPagoTarjetaUseCase(orden_repo, pago_repo, mesa_repo)

    try:
        if request.forma_pago not in ('tarjeta_debito', 'tarjeta_credito'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Forma de pago no válida para tarjeta.")

        resultado = await use_case.ejecutar(
            orden_id=request.orden_id,
            monto=request.monto,
            tipo_tarjeta=request.forma_pago.split('_')[1],
            referencia_datafono=request.referencia_datafono or '',
            cajero_id=current_user.get('id'),
        )
        return PagoResponseDTO(
            id=resultado['pago_id'],
            orden_id=request.orden_id,
            forma_pago=request.forma_pago,
            monto=request.monto,
            monto_recibido=None,
            cambio_entregado=None,
            referencia_datafono=request.referencia_datafono,
            numero_comprobante=None,
            cajero_id=current_user.get('id'),
            created_at=datetime.utcnow(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@pago_router.post(
    "/transferencia",
    summary="Registrar pago por transferencia",
    response_model=PagoResponseDTO,
    status_code=201,
    description="Registra un pago por Nequi, Daviplata o PSE con número de comprobante."
)
async def registrar_pago_transferencia(
    request: PagoRequestDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> PagoResponseDTO:
    if current_user.get('rol') not in ('mesero', 'cajero', 'administrador'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para registrar pagos.")

    rid = current_user["restaurante_id"]
    orden_repo = OrdenRepoSQLAlchemy(db, rid)
    pago_repo = PagoRepoSQLAlchemy(db)
    mesa_repo = MesaRepoSQLAlchemy(db, rid)
    use_case = RegistrarPagoTransferenciaUseCase(orden_repo, pago_repo, mesa_repo)

    try:
        if request.forma_pago not in ('nequi', 'daviplata', 'pse'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Forma de pago no válida para transferencia.")

        resultado = await use_case.ejecutar(
            orden_id=request.orden_id,
            monto=request.monto,
            tipo_transferencia=request.forma_pago,
            numero_comprobante=request.numero_comprobante or '',
            cajero_id=current_user.get('id'),
        )
        return PagoResponseDTO(
            id=resultado['pago_id'],
            orden_id=request.orden_id,
            forma_pago=request.forma_pago,
            monto=request.monto,
            monto_recibido=None,
            cambio_entregado=None,
            referencia_datafono=None,
            numero_comprobante=request.numero_comprobante,
            cajero_id=current_user.get('id'),
            created_at=datetime.utcnow(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@pago_router.post(
    "/mixto",
    summary="Registrar pago mixto",
    status_code=201,
    description="Registra varios pagos para cubrir una misma orden (pago mixto)."
)
async def registrar_pago_mixto(
    request: PagoMixtoRequestDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    if current_user.get('rol') not in ('mesero', 'cajero', 'administrador'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para registrar pagos.")

    rid = current_user["restaurante_id"]
    orden_repo = OrdenRepoSQLAlchemy(db, rid)
    pago_repo = PagoRepoSQLAlchemy(db)
    mesa_repo = MesaRepoSQLAlchemy(db, rid)
    use_case = RegistrarPagoMixtoUC(orden_repo, pago_repo, mesa_repo)

    try:
        pagos = [p.dict() for p in request.pagos]
        resultado = await use_case.ejecutar(
            orden_id=request.orden_id,
            pagos=pagos,
            cajero_id=current_user.get('id'),
        )
        return {'pagos': resultado}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@pago_router.post(
    "/descuentos",
    summary="Aplicar descuento o cortesía",
    status_code=201,
    description="Registra un descuento para una orden. Descuentos > 10% requieren administrador."
)
async def aplicar_descuento(
    request: DescuentoRequestDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    if current_user.get('rol') not in ('mesero', 'cajero', 'administrador'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para aplicar descuentos.")

    rid = current_user["restaurante_id"]
    orden_repo = OrdenRepoSQLAlchemy(db, rid)
    descuento_repo = DescuentoRepoSQLAlchemy(db)
    use_case = AplicarDescuentoUC(orden_repo, descuento_repo)

    try:
        descuento = await use_case.ejecutar(
            orden_id=request.orden_id,
            porcentaje=Decimal(str(request.porcentaje)),
            motivo=request.motivo,
            autorizado_por=current_user.get('id') if request.porcentaje > Decimal('10') else None,
            requirio_pin=request.pin_administrador is not None,
            actor_rol=current_user.get('rol'),
        )
        return {
            'id': descuento.id,
            'orden_id': descuento.orden_id,
            'porcentaje': float(descuento.porcentaje),
            'monto': descuento.monto,
            'motivo': descuento.motivo,
            'autorizado_por': descuento.autorizado_por,
            'requirio_pin': descuento.requirio_pin,
            'created_at': descuento.created_at,
        }
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@pago_router.post(
    "/cierre-caja",
    summary="Registrar cierre de caja diario",
    response_model=CierreCajaResponseDTO,
    status_code=201,
    description="Genera el cierre de caja con cuadre de efectivo, tarjeta y transferencias."
)
async def registrar_cierre_caja(
    request: CierreCajaRequestDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CierreCajaResponseDTO:
    if current_user.get('rol') not in ('cajero', 'administrador'):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo cajeros pueden registrar cierre de caja.")

    use_case = RegistrarCierreCajaUC(db, current_user["restaurante_id"])

    try:
        cierre = await use_case.ejecutar(
            fecha=request.fecha,
            total_efectivo_contado=Decimal(str(request.total_efectivo_contado)),
            observaciones=request.observaciones,
            cajero_id=current_user.get('id'),
        )
        return CierreCajaResponseDTO(
            id=cierre.id,
            fecha=cierre.fecha,
            cajero_id=current_user.get('id'),
            total_ventas=cierre.total_ventas,
            total_efectivo_sistema=cierre.total_efectivo_sistema,
            total_efectivo_contado=cierre.total_efectivo_contado,
            diferencia_efectivo=cierre.diferencia_efectivo,
            total_tarjeta=cierre.total_tarjeta,
            total_transferencia=cierre.total_transferencia,
            total_cortesia=cierre.total_cortesia,
            total_descuentos=cierre.total_descuentos,
            observaciones=cierre.observaciones,
            firmado_at=cierre.firmado_at,
            created_at=cierre.created_at,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
