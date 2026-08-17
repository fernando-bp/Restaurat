from __future__ import annotations
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.mesa_repository import MesaRepository
from app.domain.entities.mesa import Mesa
from app.infrastructure.database.models.mesa import MesaORM
from app.infrastructure.mappers.mesa_mapper import mesa_from_orm, orm_from_mesa


class MesaRepoSQLAlchemy(MesaRepository):
    def __init__(self, session: AsyncSession, restaurante_id: int = 1):
        self.session = session
        self.restaurante_id = restaurante_id

    async def obtener_por_id(self, mesa_id: int) -> Mesa | None:
        query = select(MesaORM).where(
            MesaORM.id == mesa_id,
            MesaORM.restaurante_id == self.restaurante_id,
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return mesa_from_orm(orm) if orm else None

    async def listar(self) -> list[Mesa]:
        query = select(MesaORM).where(
            MesaORM.activa == True,
            MesaORM.restaurante_id == self.restaurante_id,
        )
        result = await self.session.execute(query)
        rows = result.scalars().all()
        return [mesa_from_orm(row) for row in rows]

    async def guardar(self, mesa: Mesa) -> Mesa:
        if mesa.id is None:
            data = orm_from_mesa(mesa)
            data.pop("id", None)
            orm = MesaORM(**data)
            orm.restaurante_id = self.restaurante_id
            self.session.add(orm)
            await self.session.commit()
            await self.session.refresh(orm)
            return mesa_from_orm(orm)
        else:
            query = select(MesaORM).where(
                MesaORM.id == mesa.id,
                MesaORM.restaurante_id == self.restaurante_id,
            )
            result = await self.session.execute(query)
            orm = result.scalar_one_or_none()
            if orm:
                orm.estado = mesa.estado
                orm.numero = mesa.numero
                orm.capacidad = mesa.capacidad
                orm.zona = mesa.zona
                orm.activa = mesa.activa
                await self.session.commit()
                await self.session.refresh(orm)
                return mesa_from_orm(orm)
            return mesa

    async def eliminar(self, mesa_id: int) -> None:
        query = select(MesaORM).where(
            MesaORM.id == mesa_id,
            MesaORM.restaurante_id == self.restaurante_id,
        )
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if orm:
            orm.activa = False
            await self.session.commit()

    async def obtener_estado_mesas(self, zona: Optional[str] = None) -> list[dict]:
        if zona:
            result = await self.session.execute(
                text("SELECT * FROM v_mesas_estado WHERE restaurante_id = :rid AND zona = :zona"),
                {"rid": self.restaurante_id, "zona": zona},
            )
        else:
            result = await self.session.execute(
                text("SELECT * FROM v_mesas_estado WHERE restaurante_id = :rid"),
                {"rid": self.restaurante_id},
            )

        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

    async def obtener_estado_mesa(self, mesa_id: int) -> dict | None:
        result = await self.session.execute(
            text("SELECT * FROM v_mesas_estado WHERE restaurante_id = :rid AND id = :id"),
            {"rid": self.restaurante_id, "id": mesa_id},
        )
        row = result.fetchone()
        return dict(row._mapping) if row else None
