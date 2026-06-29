from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.reserva_repository import ReservaRepository
from app.domain.entities.reserva import Reserva
from app.infrastructure.database.models.mesa import ReservaORM
from app.infrastructure.mappers.reserva_mapper import reserva_from_orm, orm_from_reserva


class ReservaRepoSQLAlchemy(ReservaRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def obtener_por_id(self, reserva_id: int) -> Reserva | None:
        query = select(ReservaORM).where(ReservaORM.id == reserva_id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return reserva_from_orm(orm) if orm else None

    async def obtener_activa_por_mesa(self, mesa_id: int) -> Reserva | None:
        query = select(ReservaORM).where(
            (ReservaORM.mesa_id == mesa_id) &
            (ReservaORM.estado == 'activa')
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return reserva_from_orm(orm) if orm else None

    async def guardar(self, reserva: Reserva) -> Reserva:
        if reserva.id is None:
            data = orm_from_reserva(reserva)
            data.pop('id', None)
            orm = ReservaORM(**data)
            self.session.add(orm)
            await self.session.commit()
            await self.session.refresh(orm)
            return reserva_from_orm(orm)
        orm = await self.obtener_por_id(reserva.id)
        if orm:
            orm.mesa_id = reserva.mesa_id
            orm.nombre_cliente = reserva.nombre_cliente
            orm.telefono_cliente = reserva.telefono_cliente
            orm.fecha_reserva = reserva.fecha_reserva
            orm.hora_reserva = reserva.hora_reserva
            orm.num_personas = reserva.num_personas
            orm.notas = reserva.notas
            orm.usuario_id = reserva.usuario_id
            orm.estado = reserva.estado
            await self.session.commit()
        return reserva

    async def cancelar(self, reserva_id: int) -> None:
        reserva = await self.obtener_por_id(reserva_id)
        if reserva:
            query = select(ReservaORM).where(ReservaORM.id == reserva_id)
            result = await self.session.execute(query)
            orm = result.scalar_one_or_none()
            if orm:
                orm.estado = 'cancelada'
                await self.session.commit()
