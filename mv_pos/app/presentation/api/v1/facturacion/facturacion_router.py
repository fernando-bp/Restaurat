from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.factus_client import FactusClient
from app.application.use_cases.facturacion.procesar_factura_factus_uc import ProcesarFacturaFactusUC
from app.infrastructure.database.models.factura import FacturaORM
from app.infrastructure.repositories.factura_repo_sqlalchemy import FacturaRepoSQLAlchemy
from app.presentation.dependencies.db_deps import get_db_session
from app.presentation.dependencies.auth_deps import get_current_user
from pydantic import BaseModel, Field

facturacion_router = APIRouter(prefix="/facturacion", tags=["facturacion"])


class EmitirFacturaFactusRequest(BaseModel):
    orden_id: int = Field(..., gt=0)


@facturacion_router.get(
    "/ordenes/{orden_id}/factura/estado",
    summary="Consultar estado de factura de una orden",
    status_code=200,
)
async def consultar_estado_factura(orden_id: int, db: AsyncSession = Depends(get_db_session)):
    factura_repo = FacturaRepoSQLAlchemy(db)
    factura = await factura_repo.obtener_por_orden_id(orden_id)
    if not factura:
        return {
            "factura_id": None,
            "orden_id": orden_id,
            "estado": "pendiente",
            "numero_documento": None,
            "reference_code": None,
            "cufe": None,
            "pdf_url": None,
            "qr_url": None,
            "ultimo_error": None,
            "intentos": 0,
        }
    factura_actual = factura[0]
    estado_actual = factura_actual.estado.value if hasattr(factura_actual.estado, "value") else str(factura_actual.estado)
    if estado_actual in {"processing", "pendiente"} and factura_actual.reference_code:
        orm = await db.get(FacturaORM, factura_actual.id)
        if orm:
            try:
                factura_actual = await ProcesarFacturaFactusUC(db).sincronizar_con_factus(orm)
            except Exception:
                pass
    return {
        "factura_id": factura_actual.id,
        "orden_id": factura_actual.orden_id,
        "estado": factura_actual.estado.value if hasattr(factura_actual.estado, "value") else str(factura_actual.estado),
        "numero_documento": factura_actual.numero_documento,
        "reference_code": factura_actual.reference_code,
        "cufe": factura_actual.cufe,
        "pdf_url": factura_actual.url_documento,
        "qr_url": factura_actual.qr_url,
        "ultimo_error": getattr(factura_actual, "ultimo_error", None),
        "intentos": getattr(factura_actual, "intentos", 0),
    }


@facturacion_router.get(
    "/facturas/{factura_id}/pdf",
    summary="Descargar o redirigir el PDF de una factura",
    status_code=200,
)
async def descargar_pdf_factura(factura_id: int, db: AsyncSession = Depends(get_db_session)):
    factura_repo = FacturaRepoSQLAlchemy(db)
    factura = await factura_repo.obtener_por_id(factura_id)
    if not factura or not factura.url_documento:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No existe PDF para esta factura")
    return RedirectResponse(url=factura.url_documento)


@facturacion_router.post(
    "/facturas/{factura_id}/reintentar",
    summary="Reintentar manualmente una factura rechazada",
    status_code=200,
)
async def reintentar_factura(factura_id: int, db: AsyncSession = Depends(get_db_session)):
    factura_repo = FacturaRepoSQLAlchemy(db)
    factura = await factura_repo.obtener_por_id(factura_id)
    if not factura:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Factura no encontrada")
    use_case = ProcesarFacturaFactusUC(db)
    try:
        await use_case.ejecutar(factura.orden_id, force=True)
        return {"mensaje": "Reintento procesado"}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@facturacion_router.get(
    "/token",
    summary="Obtener token de Factus desde el backend",
    status_code=200,
)
async def obtener_token_factus():
    client = FactusClient()
    try:
        access_token = await client.get_access_token()
        return {"access_token": access_token}
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@facturacion_router.get(
    "/rangos-numeracion",
    summary="Listar rangos de numeración disponibles en Factus",
    status_code=200,
)
async def listar_rangos_numeracion_factus(
    range_id: int | None = Query(None, alias="id"),
    document: str | None = None,
    resolution_number: str | None = None,
    technical_key: str | None = None,
    is_active: bool | None = True,
):
    client = FactusClient()
    try:
        response = await client.list_numbering_ranges(
            range_id=range_id,
            document=document,
            resolution_number=resolution_number,
            technical_key=technical_key,
            is_active=is_active,
        )
        data = response.get("data", {})
        ranges = data.get("data", []) if isinstance(data, dict) else data
        return {
            "status": response.get("status"),
            "message": response.get("message"),
            "rangos": ranges if isinstance(ranges, list) else [],
        }
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@facturacion_router.post(
    "/emitir",
    summary="Emitir factura electrónica para una orden",
    status_code=201,
)
async def emitir_factura(
    request: EmitirFacturaFactusRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    if current_user.get("rol") not in ["mesero", "cajero", "administrador"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para emitir facturas.")

    use_case = ProcesarFacturaFactusUC(db)

    try:
        factura = await use_case.ejecutar(request.orden_id)
        if factura is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada")
        return {
            "mensaje": "Factura enviada a Factus",
            "factura_id": factura.id,
            "orden_id": factura.orden_id,
            "numero_documento": factura.numero_documento,
            "estado": factura.estado.value,
            "reference_code": factura.reference_code,
            "cufe": factura.cufe,
            "qr_url": factura.qr_url,
            "pdf_url": factura.pdf_url,
            "ultimo_error": factura.ultimo_error,
            "total_neto": factura.total_neto,
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
