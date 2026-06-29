from __future__ import annotations
from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.mesa_repository import MesaRepository
from app.domain.entities.mesa import Mesa
from app.infrastructure.database.models.mesa import MesaORM
from app.infrastructure.mappers.mesa_mapper import mesa_from_orm, orm_from_mesa


class MesaRepoSQLAlchemy(MesaRepository):
    """Implementación SQLAlchemy del repositorio de Mesas"""
    
    def __init__(self, session: AsyncSession):
        self.session = session

    async def obtener_por_id(self, mesa_id: int) -> Mesa | None:
        """Obtiene una mesa por ID de la tabla mesas"""
        query = select(MesaORM).where(MesaORM.id == mesa_id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        return mesa_from_orm(orm) if orm else None

    async def listar(self) -> list[Mesa]:
        """Lista todas las mesas activas"""
        query = select(MesaORM).where(MesaORM.activa == True)
        result = await self.session.execute(query)
        rows = result.scalars().all()
        return [mesa_from_orm(row) for row in rows]

    async def guardar(self, mesa: Mesa) -> Mesa:
        """Guarda o actualiza una mesa"""
        if mesa.id is None:
            data = orm_from_mesa(mesa)
            data.pop("id", None)
            orm = MesaORM(**data)
            self.session.add(orm)
            await self.session.commit()
            await self.session.refresh(orm)
            return mesa_from_orm(orm)
        else:
            # Actualizar existente
            query = select(MesaORM).where(MesaORM.id == mesa.id)
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
        """Marca una mesa como inactiva (soft delete)"""
        query = select(MesaORM).where(MesaORM.id == mesa_id)
        result = await self.session.execute(query)
        orm = result.scalar_one_or_none()
        if orm:
            orm.activa = False
            await self.session.commit()

    async def obtener_estado_mesas(self, zona: Optional[str] = None) -> list[dict]:
        """
        Obtiene estado en tiempo real desde la vista v_mesas_estado (RF-05)
        Esta es la consulta optimizada para el mapa de mesas
        """
        query_str = "SELECT * FROM v_mesas_estado"
        if zona:
            query_str += f" WHERE zona = '{zona}'"
        
        result = await self.session.execute(text(query_str))
        rows = result.fetchall()
        
        # Convertir Row a dict
        return [dict(row._mapping) for row in rows]

    async def obtener_estado_mesa(self, mesa_id: int) -> dict | None:
        """
        Obtiene estado en tiempo real de una mesa específica desde v_mesas_estado (RF-05)
        """
        query_str = f"SELECT * FROM v_mesas_estado WHERE id = {mesa_id}"
        result = await self.session.execute(text(query_str))
        row = result.fetchone()
        
        return dict(row._mapping) if row else None
