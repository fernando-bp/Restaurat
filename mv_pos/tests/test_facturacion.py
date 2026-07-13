import pytest
from datetime import datetime

from app.application.use_cases.facturacion.emitir_factura_uc import EmitirFacturaUseCase
from app.domain.entities.factura import Factura
from app.domain.entities.orden import Orden
from app.domain.entities.orden_item import OrdenItem
from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.enums.estado_factura import EstadoFacturaEnum


class FakeOrdenRepo:
    def __init__(self, orden):
        self.orden = orden

    async def obtener_por_id(self, orden_id):
        return self.orden if self.orden.id == orden_id else None


class FakeFacturaRepo:
    def __init__(self):
        self.guardadas = []

    async def guardar(self, factura):
        factura.id = 1001
        self.guardadas.append(factura)
        return factura

    async def obtener_por_orden_id(self, orden_id):
        return [f for f in self.guardadas if f.orden_id == orden_id]


class FakeDianService:
    async def emitir(self, factura):
        factura.estado = EstadoFacturaEnum.ACEPTADA
        factura.numero_documento = "FA-000001"
        factura.xml_documento = "<Factura />"
        factura.url_documento = "/media/facturas/factura-000001.xml"
        return factura


@pytest.mark.asyncio
async def test_emitir_factura_crea_registro_y_documento():
    orden = Orden(
        id=42,
        mesa_id=1,
        mesero_id=2,
        num_comensales=2,
        estado=EstadoOrdenEnum.PAGADA,
        hora_apertura=datetime.utcnow(),
        total_bruto=20000,
        total_descuento=0,
        total_iva=3800,
        total_neto=23800,
        items=[
            OrdenItem(id=1, orden_id=42, receta_id=10, cantidad=2, precio_unitario=10000, estado="servida", observaciones="")
        ],
    )

    factura_repo = FakeFacturaRepo()
    use_case = EmitirFacturaUseCase(FakeOrdenRepo(orden), factura_repo, FakeDianService())

    factura = await use_case.execute(orden_id=42, cliente_nombre="Cliente Test", cliente_nit="123456789")

    assert factura is not None
    assert factura.orden_id == 42
    assert factura.estado == EstadoFacturaEnum.ACEPTADA
    assert factura.numero_documento == "FA-000001"
    assert factura.total_neto == 23800
    assert len(factura.detalles) == 1
