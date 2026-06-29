from __future__ import annotations
from dataclasses import dataclass

from app.domain.enums.estado_mesa import EstadoMesaEnum
from app.domain.exceptions.orden_exceptions import TransicionEstadoInvalidaException

@dataclass
class Mesa:
    id: int | None
    numero: str
    capacidad: int
    estado: EstadoMesaEnum
    zona: str | None
    activa: bool

    def abrir(self) -> None:
        if self.estado != EstadoMesaEnum.LIBRE:
            raise TransicionEstadoInvalidaException(f'Mesa {self.numero} no puede abrirse desde {self.estado.value}')
        self.estado = EstadoMesaEnum.OCUPADA

    def reservar(self) -> None:
        if self.estado != EstadoMesaEnum.LIBRE:
            raise TransicionEstadoInvalidaException(f'Mesa {self.numero} solo puede reservarse si está libre')
        self.estado = EstadoMesaEnum.RESERVADA

    def solicitar_cuenta(self) -> None:
        if self.estado != EstadoMesaEnum.OCUPADA:
            raise TransicionEstadoInvalidaException('Solo mesas ocupadas pueden solicitar cuenta')
        self.estado = EstadoMesaEnum.EN_ESPERA_CUENTA

    def confirmar_llegada(self) -> None:
        if self.estado != EstadoMesaEnum.RESERVADA:
            raise TransicionEstadoInvalidaException('Solo reservas pueden convertirse en orden ocupada')
        self.estado = EstadoMesaEnum.OCUPADA

    def cancelar_reserva(self) -> None:
        if self.estado != EstadoMesaEnum.RESERVADA:
            raise TransicionEstadoInvalidaException('Solo reservas pueden cancelarse')
        self.estado = EstadoMesaEnum.LIBRE

    def liberar(self) -> None:
        if self.estado not in {EstadoMesaEnum.OCUPADA, EstadoMesaEnum.EN_ESPERA_CUENTA}:
            raise TransicionEstadoInvalidaException('Solo mesas ocupadas o en espera de cuenta pueden liberarse')
        self.estado = EstadoMesaEnum.LIBRE
