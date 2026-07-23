from __future__ import annotations
from datetime import datetime
from decimal import Decimal

from app.domain.entities.orden import Orden
from app.domain.entities.orden_item import OrdenItem
from app.domain.enums.estado_mesa import EstadoMesaEnum
from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.enums.tipo_receta import TipoRecetaEnum
from app.domain.exceptions.inventario_exceptions import StockInsuficienteOrdenException
from app.domain.exceptions.mesa_exceptions import MesaNoEncontradaException, MesaNoDisponibleException


class CrearOrdenUC:
    def __init__(self, mesa_repo, orden_repo, receta_repo, inventario_repo, ingrediente_repo=None):
        self.mesa_repo = mesa_repo
        self.orden_repo = orden_repo
        self.receta_repo = receta_repo
        self.inventario_repo = inventario_repo
        self.ingrediente_repo = ingrediente_repo

    async def execute(self, mesa_id: int, mesero_id: int, request) -> Orden:
        mesa = await self.mesa_repo.obtener_por_id(mesa_id)
        if not mesa:
            raise MesaNoEncontradaException(f"Mesa ID {mesa_id} no existe")

        if not mesa.activa:
            raise MesaNoDisponibleException(f"Mesa {mesa.numero} está inactiva")

        nuevos_items: list[OrdenItem] = []
        total_items = 0
        if request.items:
            for item in request.items:
                receta = await self.receta_repo.obtener_por_id(item.receta_id)
                if not receta:
                    raise ValueError(f"Receta {item.receta_id} no encontrada")
                if receta.tipo != TipoRecetaEnum.FINAL:
                    raise ValueError(f"La receta {item.receta_id} no es un producto final y no puede venderse directamente")

                precio_unitario = item.precio_unitario
                if precio_unitario is None:
                    if receta.precio_venta is None:
                        raise ValueError(
                            f"No se pudo obtener precio para la receta {item.receta_id}."
                        )
                    precio_unitario = receta.precio_venta

                subtotal = item.cantidad * precio_unitario
                total_items += subtotal
                nuevos_items.append(
                    OrdenItem(
                        id=None,
                        orden_id=0,
                        receta_id=item.receta_id,
                        cantidad=item.cantidad,
                        precio_unitario=precio_unitario,
                        estado='pendiente',
                        observaciones=item.notas,
                    )
                )

            await self._validar_stock_para_items(nuevos_items)

        def calcular_totales(total_bruto: int) -> tuple[int, int]:
            iva = int((Decimal(total_bruto) * Decimal('0.08')).quantize(Decimal('1')))
            return iva, int(Decimal(total_bruto) + iva)

        iva_items, total_neto_items = calcular_totales(total_items)

        if mesa.estado == EstadoMesaEnum.LIBRE:
            mesa.abrir()
            await self.mesa_repo.guardar(mesa)
            orden = Orden(
                id=None,
                mesa_id=mesa_id,
                mesero_id=mesero_id,
                num_comensales=request.num_comensales,
                estado=EstadoOrdenEnum.ABIERTA,
                hora_apertura=datetime.utcnow(),
                notas_generales=request.notas_generales,
                total_bruto=total_items,
                total_iva=iva_items,
                total_neto=total_neto_items,
                items=nuevos_items,
            )
            return await self.orden_repo.guardar(orden)

        if mesa.estado in {EstadoMesaEnum.OCUPADA, EstadoMesaEnum.EN_ESPERA_CUENTA}:
            orden_activa = await self.orden_repo.obtener_orden_activa_por_mesa(mesa_id)
            if orden_activa:
                if request.num_comensales > 0:
                    orden_activa.num_comensales = request.num_comensales
                if getattr(request, 'notas_generales', None) is not None:
                    orden_activa.notas_generales = request.notas_generales
                if nuevos_items:
                    orden_activa.items.extend(nuevos_items)
                    orden_activa.total_bruto += total_items
                    orden_activa.total_iva, orden_activa.total_neto = calcular_totales(orden_activa.total_bruto)
                return await self.orden_repo.guardar(orden_activa)

            orden = Orden(
                id=None,
                mesa_id=mesa_id,
                mesero_id=mesero_id,
                num_comensales=request.num_comensales,
                estado=EstadoOrdenEnum.ABIERTA,
                hora_apertura=datetime.utcnow(),
                notas_generales=request.notas_generales,
                total_bruto=total_items,
                total_iva=iva_items,
                total_neto=total_neto_items,
                items=nuevos_items,
            )
            return await self.orden_repo.guardar(orden)

        raise MesaNoDisponibleException(
            f"Mesa {mesa.numero} no está disponible para crear una orden."
        )

    async def _validar_stock_para_items(self, items: list[OrdenItem]) -> None:
        consumos: dict[int, float] = {}
        productos_por_ingrediente: dict[int, set[str]] = {}
        for item in items:
            receta = await self.receta_repo.obtener_por_id(item.receta_id)
            receta_nombre = receta.nombre if receta else f"Producto #{item.receta_id}"
            bom = await self.receta_repo.explotar_bom(item.receta_id, item.cantidad)
            for ingrediente_id, cantidad in bom.items():
                consumos[ingrediente_id] = consumos.get(ingrediente_id, 0.0) + float(cantidad)
                productos_por_ingrediente.setdefault(ingrediente_id, set()).add(receta_nombre)

        faltantes = []
        for ingrediente_id, cantidad in consumos.items():
            inventario = await self.inventario_repo.obtener_por_ingrediente(ingrediente_id)
            if not inventario:
                raise ValueError(f"Inventario para ingrediente {ingrediente_id} no encontrado")
            if inventario.stock_actual < cantidad:
                ingrediente = (
                    await self.ingrediente_repo.obtener_por_id(ingrediente_id)
                    if self.ingrediente_repo is not None
                    else None
                )
                unidad = (
                    await self.ingrediente_repo.obtener_unidad_base_abreviatura(ingrediente_id)
                    if self.ingrediente_repo is not None
                    else None
                )
                faltantes.append({
                    "ingrediente_id": ingrediente_id,
                    "ingrediente_nombre": ingrediente.nombre if ingrediente else f"Ingrediente #{ingrediente_id}",
                    "disponible": float(inventario.stock_actual),
                    "requerido": float(cantidad),
                    "faltante": float(cantidad - inventario.stock_actual),
                    "unidad": unidad or "",
                    "productos": sorted(productos_por_ingrediente.get(ingrediente_id, [])),
                })

        if faltantes:
            raise StockInsuficienteOrdenException(faltantes)
