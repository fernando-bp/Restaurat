from __future__ import annotations
from app.domain.entities.reserva import Reserva
from app.infrastructure.database.models.mesa import ReservaORM


def reserva_from_orm(orm: ReservaORM) -> Reserva | None:
    if orm is None:
        return None

    return Reserva(
        id=orm.id,
        mesa_id=orm.mesa_id,
        nombre_cliente=orm.nombre_cliente,
        telefono_cliente=orm.telefono_cliente,
        fecha_reserva=orm.fecha_reserva,
        hora_reserva=orm.hora_reserva,
        num_personas=orm.num_personas,
        notas=orm.notas,
        usuario_id=orm.usuario_id,
        estado=orm.estado,
        created_at=orm.created_at,
    )


def orm_from_reserva(reserva: Reserva) -> dict:
    return {
        'id': reserva.id,
        'mesa_id': reserva.mesa_id,
        'nombre_cliente': reserva.nombre_cliente,
        'telefono_cliente': reserva.telefono_cliente,
        'fecha_reserva': reserva.fecha_reserva,
        'hora_reserva': reserva.hora_reserva,
        'num_personas': reserva.num_personas,
        'notas': reserva.notas,
        'usuario_id': reserva.usuario_id,
        'estado': reserva.estado,
        'created_at': reserva.created_at,
    }
