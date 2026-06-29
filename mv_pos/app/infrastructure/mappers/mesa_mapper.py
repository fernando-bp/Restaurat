from __future__ import annotations
from typing import Optional

from app.domain.entities.mesa import Mesa
from app.domain.enums.estado_mesa import EstadoMesaEnum
from app.infrastructure.database.models.mesa import MesaORM


def mesa_from_orm(model: Optional[MesaORM]) -> Optional[Mesa]:
    """Convierte MesaORM a entidad Mesa"""
    if model is None:
        return None

    return Mesa(
        id=model.id,
        numero=model.numero,
        capacidad=model.capacidad,
        estado=EstadoMesaEnum(model.estado),
        zona=model.zona,
        activa=bool(model.activa),
    )


def orm_from_mesa(mesa: Mesa) -> dict:
    """Convierte entidad Mesa a diccionario para ORM"""
    return {
        "id": mesa.id,
        "numero": mesa.numero,
        "capacidad": mesa.capacidad,
        "estado": mesa.estado.value,
        "zona": mesa.zona,
        "activa": mesa.activa,
    }
