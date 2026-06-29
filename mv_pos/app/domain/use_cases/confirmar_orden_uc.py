from __future__ import annotations
from datetime import datetime
from pathlib import Path

from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.enums.tipo_receta import TipoRecetaEnum
from app.domain.exceptions.inventario_exceptions import StockInsuficienteOrdenException
from app.domain.exceptions.orden_exceptions import OrdenNoConfirmableException, OrdenNoEncontradaException
from app.application.dtos.comanda_dto import ComandaDTO, ComandaItemDTO
from app.application.services.comanda_service import ComandaService


class ConfirmarOrdenUC:
    def __init__(
        self,
        orden_repo,
        orden_item_repo,
        receta_repo,
        inventario_repo,
        ingrediente_repo,
        movimiento_repo,
        comanda_repo,
    ):
        self.orden_repo = orden_repo
        self.orden_item_repo = orden_item_repo
        self.receta_repo = receta_repo
        self.inventario_repo = inventario_repo
        self.ingrediente_repo = ingrediente_repo
        self.movimiento_repo = movimiento_repo
        self.comanda_repo = comanda_repo

    async def execute(self, orden_id: int, usuario_id: int):
        orden = await self.orden_repo.obtener_por_id(orden_id)
        if not orden:
            raise OrdenNoEncontradaException(f"Orden ID {orden_id} no existe")

        if orden.estado != EstadoOrdenEnum.ABIERTA:
            raise OrdenNoConfirmableException(
                f"Orden {orden_id} no puede confirmarse desde estado {orden.estado.value}"
            )

        items = await self.orden_item_repo.listar_por_orden(orden_id)
        if not items:
            raise OrdenNoConfirmableException("Orden sin items no puede confirmarse")

        items_pendientes = [item for item in items if item.estado == "pendiente"]
        if not items_pendientes:
            raise OrdenNoConfirmableException("No hay productos nuevos pendientes por enviar a cocina")

        consumos: dict[int, float] = {}
        productos_por_ingrediente: dict[int, set[str]] = {}
        for item in items_pendientes:
            receta = await self.receta_repo.obtener_por_id(item.receta_id)
            if not receta:
                raise ValueError(f"Receta {item.receta_id} no encontrada")
            if receta.tipo != TipoRecetaEnum.FINAL:
                raise ValueError(f"Receta {item.receta_id} no es un producto de venta final")

            bom = await self.receta_repo.explotar_bom(item.receta_id, item.cantidad)
            for ingrediente_id, cantidad in bom.items():
                consumos[ingrediente_id] = consumos.get(ingrediente_id, 0.0) + float(cantidad)
                productos_por_ingrediente.setdefault(ingrediente_id, set()).add(receta.nombre)

        faltantes = []
        for ingrediente_id, cantidad in consumos.items():
            inventario = await self.inventario_repo.obtener_por_ingrediente(ingrediente_id)
            if not inventario:
                raise ValueError(f"Inventario para ingrediente {ingrediente_id} no encontrado")
            if inventario.stock_actual < cantidad:
                ingrediente = await self.ingrediente_repo.obtener_por_id(ingrediente_id)
                unidad = await self.ingrediente_repo.obtener_unidad_base_abreviatura(ingrediente_id)
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

        for ingrediente_id, cantidad in consumos.items():
            inventario = await self.inventario_repo.obtener_por_ingrediente(ingrediente_id)
            if not inventario:
                raise ValueError(f"Inventario para ingrediente {ingrediente_id} no encontrado")
            inventario.descontar(cantidad)
            inventario_actualizado = await self.inventario_repo.guardar(inventario)

            ingrediente = await self.ingrediente_repo.obtener_por_id(ingrediente_id)
            precio_snap = float(ingrediente.precio_unitario) if ingrediente is not None else None

            await self.movimiento_repo.registrar(
                ingrediente_id=ingrediente_id,
                cantidad=-cantidad,
                stock_resultante=inventario_actualizado.stock_actual,
                precio_unitario_snap=precio_snap,
                usuario_id=usuario_id,
                referencia_orden=orden_id,
                motivo=f"Consumo por orden {orden_id}",
            )

        orden.hora_confirmacion = datetime.utcnow()
        orden_guardada = await self.orden_repo.guardar(orden)

        for item in items_pendientes:
            item.estado = "en_preparacion"
            await self.orden_item_repo.guardar(item)

        comanda_items: list[ComandaItemDTO] = []
        for item in items_pendientes:
            receta = await self.receta_repo.obtener_por_id(item.receta_id)
            comanda_items.append(
                ComandaItemDTO(
                    receta_nombre=receta.nombre if receta else f"Receta {item.receta_id}",
                    cantidad=item.cantidad,
                    observaciones=item.observaciones,
                )
            )

        mesa_numero = getattr(orden_guardada, "mesa_id", None)

        comanda = ComandaDTO(
            orden_id=orden_guardada.id,
            mesa_numero=mesa_numero or orden_guardada.mesa_id,
            num_comensales=orden_guardada.num_comensales,
            items=comanda_items,
            hora=orden_guardada.hora_confirmacion,
            notas_generales=orden_guardada.notas_generales,
        )

        ticket = ComandaService.generar_ticket(comanda)

        project_root = Path(__file__).resolve().parents[3]
        comandas_dir = project_root / "data" / "comandas"
        comandas_dir.mkdir(parents=True, exist_ok=True)
        timestamp = (
            orden_guardada.hora_confirmacion.strftime("%Y%m%d%H%M%S")
            if orden_guardada.hora_confirmacion
            else datetime.utcnow().strftime("%Y%m%d%H%M%S")
        )
        filename = f"comanda_{orden_guardada.id}_{timestamp}.txt"
        file_path = str(comandas_dir / filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(ticket)

        if self.comanda_repo is not None:
            await self.comanda_repo.crear(
                orden_id=orden_guardada.id,
                mesa_id=orden_guardada.mesa_id,
                contenido=ticket,
                file_path=file_path,
            )

        return orden_guardada, ticket
