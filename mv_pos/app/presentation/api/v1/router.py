from fastapi import APIRouter

from app.presentation.api.v1.auth.auth_router import auth_router
# from app.presentation.api.v1.media.media_router import router as media_router
from app.presentation.api.v1.mesas.mesa_router import mesa_router
from app.presentation.api.v1.ordenes.orden_router import orden_router
from app.presentation.api.v1.pagos.pago_router import pago_router
from app.presentation.api.v1.pagos.cierre_caja_router import cierre_caja_router
from app.presentation.api.v1.pagos.pago_dividido_router import pago_dividido_router
from app.presentation.api.v1.recetas.receta_router import receta_router
from app.presentation.api.v1.inventario.inventario_router import inventario_router
from app.presentation.api.v1.ingredientes.ingrediente_router import ingrediente_router
from app.presentation.api.v1.reportes_financieros.reporte_router import reporte_financiero_router
from app.presentation.api.v1.facturacion.facturacion_router import facturacion_router
from app.integrations.bold_qr.router import bold_qr_router
from app.integrations.bold_qr_test.router import bold_qr_test_router
from app.integrations.bold_terminal.router import router as bold_terminal_router, webhook_router as bold_webhook_router


def create_v1_router() -> APIRouter:
    router = APIRouter()
    router.include_router(auth_router)
    # router.include_router(media_router)
    router.include_router(mesa_router)
    router.include_router(orden_router)
    router.include_router(pago_router)
    router.include_router(cierre_caja_router)
    router.include_router(pago_dividido_router)
    router.include_router(receta_router)
    router.include_router(inventario_router)
    router.include_router(ingrediente_router)
    router.include_router(reporte_financiero_router)
    router.include_router(facturacion_router)
    router.include_router(bold_qr_router)
    router.include_router(bold_qr_test_router)
    router.include_router(bold_terminal_router)
    router.include_router(bold_webhook_router)
    return router
