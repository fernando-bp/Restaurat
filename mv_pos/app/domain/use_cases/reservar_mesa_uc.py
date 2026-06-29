from __future__ import annotations
from app.domain.repositories.mesa_repository import MesaRepository
from app.domain.repositories.reserva_repository import ReservaRepository
from app.application.dtos.mesa_dto import (
    ReservarMesaRequestDTO,
    ReservarMesaResponseDTO,
    ReservarMesasResponseDTO,
)
from app.domain.entities.reserva import Reserva
from app.domain.enums.estado_mesa import EstadoMesaEnum
from app.domain.exceptions.mesa_exceptions import (
    MesaNoEncontradaException,
    MesaNoDisponibleException,
    CapacidadMesaExcedidaException,
    ReservaMesaException,
)


class ReservarMesaUC:
    """Use Case: Crear una reserva de mesa (RF-08)"""

    def __init__(
        self,
        mesa_repo: MesaRepository,
        reserva_repo: ReservaRepository
    ):
        self.mesa_repo = mesa_repo
        self.reserva_repo = reserva_repo

    async def execute(
        self,
        mesa_id: int,
        usuario_id: int,
        request: ReservarMesaRequestDTO
    ) -> ReservarMesaResponseDTO:
        """Crea una reserva y marca la mesa como reservada."""

        mesa = await self.mesa_repo.obtener_por_id(mesa_id)
        if not mesa:
            raise MesaNoEncontradaException(f"Mesa ID {mesa_id} no existe")

        if not mesa.activa:
            raise MesaNoDisponibleException(f"Mesa {mesa.numero} está inactiva")

        if mesa.estado.value != 'libre':
            raise MesaNoDisponibleException(
                f"Mesa {mesa.numero} está {mesa.estado.value}. Solo se pueden reservar mesas libres."
            )

        if request.num_personas > mesa.capacidad:
            raise CapacidadMesaExcedidaException(
                f"Mesa {mesa.numero} tiene capacidad máxima de {mesa.capacidad} personas"
            )

        reserva_activa = await self.reserva_repo.obtener_activa_por_mesa(mesa_id)
        if reserva_activa:
            raise ReservaMesaException(
                f"Ya existe una reserva activa para la mesa {mesa.numero}."
            )

        mesa.reservar()
        await self.mesa_repo.guardar(mesa)

        reserva = Reserva(
            id=None,
            mesa_id=mesa_id,
            nombre_cliente=request.nombre_cliente,
            telefono_cliente=request.telefono_cliente,
            fecha_reserva=request.fecha_reserva,
            hora_reserva=request.hora_reserva,
            num_personas=request.num_personas,
            notas=request.notas,
            usuario_id=usuario_id,
            estado='activa'
        )

        reserva_guardada = await self.reserva_repo.guardar(reserva)

        return ReservarMesaResponseDTO(
            reserva_id=reserva_guardada.id,
            mesa_id=mesa_id,
            mesa_numero=mesa.numero,
            nombre_cliente=request.nombre_cliente,
            telefono_cliente=request.telefono_cliente,
            fecha_reserva=request.fecha_reserva,
            hora_reserva=request.hora_reserva,
            num_personas=request.num_personas,
            estado_reserva=reserva_guardada.estado,
            mensaje=f"Mesa {mesa.numero} reservada para {request.nombre_cliente} el {request.fecha_reserva} a las {request.hora_reserva}."
        )


class ReservarMesasUC:
    """Use Case: Crear reservas para una o varias mesas"""

    def __init__(
        self,
        mesa_repo,
        reserva_repo
    ):
        self.mesa_repo = mesa_repo
        self.reserva_repo = reserva_repo

    async def execute(
        self,
        mesa_ids: list[int],
        usuario_id: int,
        request: ReservarMesaRequestDTO
    ) -> ReservarMesasResponseDTO:
        """Crea reservas para varias mesas y marca cada mesa como reservada."""

        if not mesa_ids:
            raise ReservaMesaException("Debe especificar al menos una mesa para reservar.")

        if len(set(mesa_ids)) != len(mesa_ids):
            raise ReservaMesaException("No se pueden reservar mesas duplicadas en la misma solicitud.")

        mesas = []
        capacidad_total = 0

        for mesa_id in mesa_ids:
            mesa = await self.mesa_repo.obtener_por_id(mesa_id)
            if not mesa:
                raise MesaNoEncontradaException(f"Mesa ID {mesa_id} no existe")

            if not mesa.activa:
                raise MesaNoDisponibleException(f"Mesa {mesa.numero} está inactiva")

            estado = mesa.estado.value if hasattr(mesa.estado, 'value') else str(mesa.estado)
            if estado != 'libre':
                raise MesaNoDisponibleException(
                    f"Mesa {mesa.numero} está {estado}. Solo se pueden reservar mesas libres."
                )

            reserva_activa = await self.reserva_repo.obtener_activa_por_mesa(mesa_id)
            if reserva_activa:
                raise ReservaMesaException(
                    f"Ya existe una reserva activa para la mesa {mesa.numero}."
                )

            mesas.append(mesa)
            capacidad_total += mesa.capacidad

        if request.num_personas > capacidad_total:
            raise CapacidadMesaExcedidaException(
                f"Capacidad total de mesas seleccionadas es {capacidad_total} personas, "
                f"pero se solicitan {request.num_personas}."
            )

        reservas = []
        for mesa in mesas:
            mesa.reservar()
            await self.mesa_repo.guardar(mesa)

            reserva = Reserva(
                id=None,
                mesa_id=mesa.id,
                nombre_cliente=request.nombre_cliente,
                telefono_cliente=request.telefono_cliente,
                fecha_reserva=request.fecha_reserva,
                hora_reserva=request.hora_reserva,
                num_personas=request.num_personas,
                notas=request.notas,
                usuario_id=usuario_id,
                estado='activa'
            )

            reservas.append(await self.reserva_repo.guardar(reserva))

        return ReservarMesasResponseDTO(
            reservas=[
                ReservarMesaResponseDTO(
                    reserva_id=reserva.id,
                    mesa_id=reserva.mesa_id,
                    mesa_numero=next(m.numero for m in mesas if m.id == reserva.mesa_id),
                    nombre_cliente=reserva.nombre_cliente,
                    telefono_cliente=reserva.telefono_cliente,
                    fecha_reserva=reserva.fecha_reserva,
                    hora_reserva=reserva.hora_reserva,
                    num_personas=reserva.num_personas,
                    estado_reserva=reserva.estado,
                    mensaje=f"Mesa {next(m.numero for m in mesas if m.id == reserva.mesa_id)} reservada para {reserva.nombre_cliente} el {reserva.fecha_reserva} a las {reserva.hora_reserva}."
                )
                for reserva in reservas
            ],
            total_reservas=len(reservas),
            mensaje=(
                f"Se reservaron {len(reservas)} mesa(s) para {request.nombre_cliente}."
            )
        )
