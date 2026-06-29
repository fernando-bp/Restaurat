from __future__ import annotations
from datetime import datetime

from app.domain.repositories.orden_repository import OrdenRepository
from app.domain.repositories.mesa_repository import MesaRepository
from app.application.dtos.transferencia_union_dto import UnirMesasRequestDTO, UnirMesasResponseDTO
from app.domain.entities.orden_item import OrdenItem
from app.domain.exceptions.orden_exceptions import UnionMesasException
from app.domain.exceptions.mesa_exceptions import MesaNoEncontradaException
from app.domain.enums.estado_mesa import EstadoMesaEnum


class UnirMesasUC:
    """
    Use Case: Unir dos mesas en una sola cuenta
    
    Requisito: El sistema debe permitir unir dos mesas en una sola orden,
    consolidando los ítems en una sola orden sin pérdida de información.
    
    Pasos:
    1. Validar que ambas mesas existen y están activas
    2. Validar que ambas mesas están ocupadas
    3. Validar que son mesas diferentes
    4. Obtener orden activa de mesa origen
    5. Obtener orden activa de mesa destino
    6. Copiar todos los items de orden origen a orden destino (CREAR nuevos registros)
    7. Actualizar num_comensales en orden destino
    8. Eliminar orden origen
    9. Cambiar estado de mesa origen a 'libre'
    10. Retornar confirmación de unión
    
    IMPORTANTE: Se crean NUEVOS registros de orden_items, no se modifican existentes.
    Esto preserva la integridad referencial y el historial.
    """

    def __init__(
        self,
        orden_repo: OrdenRepository,
        mesa_repo: MesaRepository
    ):
        self.orden_repo = orden_repo
        self.mesa_repo = mesa_repo

    async def execute(
        self,
        request: UnirMesasRequestDTO
    ) -> UnirMesasResponseDTO:
        """
        Une dos mesas en una sola orden
        
        Args:
            request: DTO con mesa_origen_id y mesa_destino_id
            
        Returns:
            UnirMesasResponseDTO con confirmación
            
        Raises:
            UnionMesasException: Si validación falla
            MesaNoEncontradaException: Si alguna mesa no existe
        """

        # Paso 1: Validar que mesas son diferentes
        if request.mesa_origen_id == request.mesa_destino_id:
            raise UnionMesasException(
                "No se puede unir una mesa consigo misma. "
                "Mesa origen y destino deben ser diferentes."
            )

        # Paso 2: Obtener y validar mesa origen
        mesa_origen = await self.mesa_repo.obtener_por_id(request.mesa_origen_id)
        if not mesa_origen:
            raise MesaNoEncontradaException(
                f"Mesa origen ID {request.mesa_origen_id} no existe"
            )

        if not mesa_origen.activa:
            raise UnionMesasException(
                f"Mesa origen {mesa_origen.numero} está inactiva"
            )

        estado_origen = mesa_origen.estado.value if hasattr(mesa_origen.estado, 'value') else str(mesa_origen.estado)
        if estado_origen != 'ocupada':
            raise UnionMesasException(
                f"Mesa origen {mesa_origen.numero} debe estar ocupada. "
                f"Estado actual: {estado_origen}"
            )

        # Paso 3: Obtener y validar mesa destino
        mesa_destino = await self.mesa_repo.obtener_por_id(request.mesa_destino_id)
        if not mesa_destino:
            raise MesaNoEncontradaException(
                f"Mesa destino ID {request.mesa_destino_id} no existe"
            )

        if not mesa_destino.activa:
            raise UnionMesasException(
                f"Mesa destino {mesa_destino.numero} está inactiva"
            )

        estado_destino = mesa_destino.estado.value if hasattr(mesa_destino.estado, 'value') else str(mesa_destino.estado)
        if estado_destino not in ['ocupada', 'libre']:
            raise UnionMesasException(
                f"Mesa destino {mesa_destino.numero} debe estar ocupada o libre. "
                f"Estado actual: {estado_destino}"
            )

        # Paso 4: Obtener orden activa de mesa origen
        ordenes_origen = await self.orden_repo.listar_por_mesa(request.mesa_origen_id)
        orden_origen = None
        for o in ordenes_origen:
            estado = o.estado.value if hasattr(o.estado, 'value') else str(o.estado)
            if estado not in ['pagada', 'cancelada']:
                orden_origen = o
                break

        if not orden_origen:
            raise UnionMesasException(
                f"No existe orden activa en mesa origen {mesa_origen.numero}"
            )

        # Si la mesa destino está libre, trasladar la orden completa a la mesa destino
        if estado_destino == 'libre':
            orden_origen.mesa_id = mesa_destino.id
            orden_destino_actualizada = await self.orden_repo.guardar(orden_origen)

            mesa_destino.estado = EstadoMesaEnum.OCUPADA
            await self.mesa_repo.guardar(mesa_destino)

            mesa_origen.estado = EstadoMesaEnum.LIBRE
            await self.mesa_repo.guardar(mesa_origen)

            return UnirMesasResponseDTO(
                orden_destino_id=orden_destino_actualizada.id,
                mesa_destino_id=mesa_destino.id,
                mesa_destino_numero=mesa_destino.numero,
                orden_origen_id=orden_origen.id,
                mesa_origen_id=mesa_origen.id,
                mesa_origen_numero=mesa_origen.numero,
                num_items_consolidados=0,
                nuevo_total_comensales=orden_origen.num_comensales,
                hora_union=datetime.utcnow(),
                mensaje=(
                    f"Orden {orden_origen.id} trasladada de mesa {mesa_origen.numero} "
                    f"a mesa {mesa_destino.numero}."
                )
            )

        # Paso 5: Obtener orden activa de mesa destino
        ordenes_destino = await self.orden_repo.listar_por_mesa(request.mesa_destino_id)
        orden_destino = None
        for o in ordenes_destino:
            estado = o.estado.value if hasattr(o.estado, 'value') else str(o.estado)
            if estado not in ['pagada', 'cancelada']:
                orden_destino = o
                break

        if not orden_destino:
            raise UnionMesasException(
                f"No existe orden activa en mesa destino {mesa_destino.numero}"
            )

        # Paso 6: Copiar items de orden origen a destino
        # CRÍTICO: Crear NUEVOS registros, no modificar existentes
        items_copiados = 0
        if hasattr(orden_origen, 'items') and orden_origen.items:
            for item_origen in orden_origen.items:
                # Crear nuevo OrdenItem con mismos datos pero referencia a nueva orden
                item_nuevo = OrdenItem(
                    id=None,  # Será asignado por BD
                    orden_id=orden_destino.id,
                    receta_id=item_origen.receta_id,
                    cantidad=item_origen.cantidad,
                    precio_unitario=item_origen.precio_unitario,
                    estado=item_origen.estado,
                    modificadores=item_origen.modificadores,
                    notas=item_origen.notas
                )
                # Agregar a orden destino
                orden_destino.items.append(item_nuevo)
                items_copiados += 1

        # Paso 7: Actualizar num_comensales en orden destino
        num_comensales_destino = (
            orden_destino.num_comensales + orden_origen.num_comensales
        )
        orden_destino.num_comensales = num_comensales_destino

        # Paso 8: Guardar orden destino con items nuevos
        orden_destino_actualizada = await self.orden_repo.guardar(orden_destino)

        # Paso 9: Eliminar orden origen
        await self.orden_repo.eliminar(orden_origen.id)

        # Paso 10: Cambiar estado de mesa origen a 'libre'
        mesa_origen.estado = EstadoMesaEnum.LIBRE
        mesa_origen_actualizada = await self.mesa_repo.guardar(mesa_origen)

        # Paso 11: Retornar respuesta
        return UnirMesasResponseDTO(
            orden_destino_id=orden_destino_actualizada.id,
            mesa_destino_id=mesa_destino.id,
            mesa_destino_numero=mesa_destino.numero,
            orden_origen_id=orden_origen.id,
            mesa_origen_id=mesa_origen.id,
            mesa_origen_numero=mesa_origen.numero,
            num_items_consolidados=items_copiados,
            nuevo_total_comensales=num_comensales_destino,
            hora_union=datetime.utcnow(),
            mensaje=f"Mesas {mesa_origen.numero} y {mesa_destino.numero} unidas exitosamente. "
                    f"{items_copiados} ítems consolidados en orden {orden_destino_actualizada.id}"
        )
