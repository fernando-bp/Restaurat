from __future__ import annotations
from typing import Optional
from datetime import datetime

from app.domain.repositories.mesa_repository import MesaRepository
from app.domain.repositories.orden_repository import OrdenRepository
from app.application.dtos.mesa_dto import AbrirMesaRequestDTO, AbrirMesaResponseDTO
from app.domain.entities.orden import Orden
from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.exceptions.mesa_exceptions import (
    MesaNoEncontradaException,
    MesaNoDisponibleException,
    CapacidadMesaExcedidaException
)


class AbrirMesaUC:
    """Use Case: Abrir una mesa e iniciar orden (RF-06)"""

    def __init__(self, mesa_repo: MesaRepository, orden_repo: OrdenRepository):
        self.mesa_repo = mesa_repo
        self.orden_repo = orden_repo

    async def execute(
        self,
        mesa_id: int,
        mesero_id: int,
        mesero_nombre: str,
        request: AbrirMesaRequestDTO
    ) -> AbrirMesaResponseDTO:
        """
        Abre una mesa y crea una orden asociada

        Pasos:
        1. Validar que mesa existe y está activa
        2. Validar que mesa está en estado 'libre'
        3. Validar capacidad de la mesa
        4. Cambiar estado mesa a 'ocupada'
        5. Crear nueva orden con mesero asignado
        6. Retornar datos de confirmación

        Args:
            mesa_id: ID de la mesa
            mesero_id: ID del mesero que abre la mesa
            mesero_nombre: Nombre del mesero
            request: Datos de apertura (num_comensales)

        Returns:
            AbrirMesaResponseDTO con confirmación

        Raises:
            MesaNoEncontradaException
            MesaNoDisponibleException
            CapacidadMesaExcedidaException
        """

        # Paso 1: Obtener mesa
        mesa = await self.mesa_repo.obtener_por_id(mesa_id)
        if not mesa:
            raise MesaNoEncontradaException(f"Mesa ID {mesa_id} no existe")

        # Paso 2: Validar que la mesa está activa
        if not mesa.activa:
            raise MesaNoDisponibleException(f"Mesa {mesa.numero} está inactiva")

        # Paso 3: Validar estado (debe estar libre)
        if mesa.estado.value != 'libre':
            raise MesaNoDisponibleException(
                f"Mesa {mesa.numero} está {mesa.estado.value}. Solo se puede abrir mesas libres."
            )

        # Paso 4: Validar capacidad
        if request.num_comensales > mesa.capacidad:
            raise CapacidadMesaExcedidaException(
                f"Mesa {mesa.numero} tiene capacidad máxima de {mesa.capacidad} personas"
            )

        # Paso 5: Cambiar estado a ocupada
        mesa.abrir()
        mesa_actualizada = await self.mesa_repo.guardar(mesa)

        # Paso 6: Crear orden
        orden = Orden(
            id=None,
            mesa_id=mesa_id,
            mesero_id=mesero_id,
            num_comensales=request.num_comensales,
            estado=EstadoOrdenEnum.ABIERTA,
            hora_apertura=datetime.utcnow()
        )
        orden_creada = await self.orden_repo.guardar(orden)

        # Paso 7: Retornar respuesta
        return AbrirMesaResponseDTO(
            mesa_id=mesa_id,
            mesa_numero=mesa.numero,
            orden_id=orden_creada.id,
            mesero_id=mesero_id,
            mesero_nombre=mesero_nombre,
            num_comensales=request.num_comensales,
            hora_apertura=orden_creada.hora_apertura,
            estado_mesa='ocupada',
            mensaje=f"Mesa {mesa.numero} abierta para {request.num_comensales} persona(s)"
        )
