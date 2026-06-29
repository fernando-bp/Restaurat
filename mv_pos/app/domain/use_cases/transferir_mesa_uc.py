from __future__ import annotations
from datetime import datetime

from app.domain.repositories.orden_repository import OrdenRepository
from app.domain.repositories.usuario_repository import UsuarioRepository
from app.application.dtos.transferencia_union_dto import TransferirMesaRequestDTO, TransferirMesaResponseDTO
from app.domain.exceptions.orden_exceptions import TransferenciaMesaException
from app.domain.exceptions.auth_exceptions import UsuarioNoEncontradoException


class TransferirMesaUC:
    """
    Use Case: Transferir una mesa a otro mesero
    
    Requisito: El sistema debe permitir transferir una mesa a otro mesero.
    La transferencia solo aplica a la orden activa en la mesa.
    
    Pasos:
    1. Validar que orden existe y está activa (no pagada ni cancelada)
    2. Validar que nuevo mesero existe y está activo
    3. Validar que nuevo mesero tiene rol de 'mesero'
    4. Cambiar mesero_id en la orden
    5. Retornar confirmación de transferencia
    """

    def __init__(
        self, 
        orden_repo: OrdenRepository,
        usuario_repo: UsuarioRepository
    ):
        self.orden_repo = orden_repo
        self.usuario_repo = usuario_repo

    async def execute(
        self,
        orden_id: int,
        mesero_id_anterior: int,
        mesero_nombre_anterior: str,
        nuevo_mesero_id: int,
        request: TransferirMesaRequestDTO
    ) -> TransferirMesaResponseDTO:
        """
        Transfiere una orden a otro mesero
        
        Args:
            orden_id: ID de la orden a transferir
            mesero_id_anterior: ID del mesero actual (para auditoría)
            mesero_nombre_anterior: Nombre del mesero actual
            nuevo_mesero_id: ID del nuevo mesero
            request: DTO con datos de transferencia
            
        Returns:
            TransferirMesaResponseDTO con confirmación
            
        Raises:
            TransferenciaMesaException: Si validación falla
            UsuarioNoEncontradoException: Si nuevo mesero no existe
        """

        # Paso 1: Obtener orden
        orden = await self.orden_repo.obtener_por_id(orden_id)
        if not orden:
            raise TransferenciaMesaException(f"Orden ID {orden_id} no existe")

        # Validar que está activa (no pagada ni cancelada)
        estado_valor = orden.estado.value if hasattr(orden.estado, 'value') else str(orden.estado)
        if estado_valor in ['pagada', 'cancelada']:
            raise TransferenciaMesaException(
                f"No se puede transferir orden en estado '{estado_valor}'. "
                f"Solo se pueden transferir órdenes activas."
            )

        # Paso 2: Validar nuevo mesero existe
        nuevo_mesero = await self.usuario_repo.obtener_por_id(request.nuevo_mesero_id)
        if not nuevo_mesero:
            raise UsuarioNoEncontradoException(
                f"Mesero ID {request.nuevo_mesero_id} no existe"
            )

        # Validar que está activo
        if not nuevo_mesero.activo:
            raise TransferenciaMesaException(
                f"Mesero {nuevo_mesero.nombre_completo} está inactivo"
            )

        # Validar que tiene rol de 'mesero' o superior (admin)
        rol_nombre = nuevo_mesero.rol.nombre if hasattr(nuevo_mesero, 'rol') else ''
        if rol_nombre not in ['mesero', 'administrador']:
            raise TransferenciaMesaException(
                f"Usuario {nuevo_mesero.nombre_completo} no es mesero. "
                f"Solo meseros pueden recibir mesas."
            )

        # Paso 3: Cambiar mesero en la orden
        mesero_anterior = orden.mesero_id
        orden.mesero_id = request.nuevo_mesero_id
        orden.transferencia_a_mesero_id = request.nuevo_mesero_id
        
        # Guardar cambios
        orden_actualizada = await self.orden_repo.guardar(orden)

        # Paso 4: Retornar respuesta
        return TransferirMesaResponseDTO(
            orden_id=orden_actualizada.id,
            mesa_id=orden_actualizada.mesa_id,
            mesa_numero=getattr(orden_actualizada, 'mesa_numero', 'N/A'),
            mesero_id_anterior=mesero_anterior,
            mesero_anterior_nombre=mesero_nombre_anterior,
            mesero_id_nuevo=request.nuevo_mesero_id,
            mesero_nuevo_nombre=nuevo_mesero.nombre_completo,
            hora_transferencia=datetime.utcnow(),
            mensaje=f"Orden {orden_actualizada.id} transferida de {mesero_nombre_anterior} "
                    f"a {nuevo_mesero.nombre_completo} exitosamente"
        )
