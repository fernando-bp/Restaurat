from __future__ import annotations
from typing import Optional
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.usuario_repository import UsuarioRepository
from app.infrastructure.database.models.usuario import UsuarioORM
from app.infrastructure.database.models.empleado import EmpleadoORM
from app.infrastructure.mappers.usuario_mapper import usuario_from_orm, orm_from_usuario
from app.domain.entities.usuario import Usuario


class UsuarioRepoSQLAlchemy(UsuarioRepository):
    def __init__(self, session: AsyncSession, restaurante_id: int = 1):
        self.session = session
        self.restaurante_id = restaurante_id

    async def obtener_por_id(self, usuario_id: int) -> Usuario | None:
        q = select(UsuarioORM).where(
            UsuarioORM.id == usuario_id,
            UsuarioORM.restaurante_id == self.restaurante_id,
        )
        res = await self.session.execute(q)
        orm = res.scalar_one_or_none()
        return usuario_from_orm(orm)

    async def obtener_por_username(self, username: str) -> Usuario | None:
        q = select(UsuarioORM).where(
            UsuarioORM.username == username,
            UsuarioORM.restaurante_id == self.restaurante_id,
        )
        res = await self.session.execute(q)
        orm = res.scalar_one_or_none()
        return usuario_from_orm(orm)

    async def obtener_por_email(self, email: str) -> Usuario | None:
        q = (
            select(UsuarioORM)
            .join(EmpleadoORM, EmpleadoORM.usuario_id == UsuarioORM.id)
            .where(
                EmpleadoORM.email == email,
                UsuarioORM.restaurante_id == self.restaurante_id,
            )
        )
        res = await self.session.execute(q)
        orm = res.scalar_one_or_none()
        return usuario_from_orm(orm)

    async def listar(self) -> list[Usuario]:
        q = select(UsuarioORM).where(UsuarioORM.restaurante_id == self.restaurante_id)
        res = await self.session.execute(q)
        rows = res.scalars().all()
        return [usuario_from_orm(r) for r in rows]

    async def agregar(self, usuario: Usuario) -> Usuario:
        if usuario.id is None:
            data = orm_from_usuario(usuario)
            data.pop("id", None)
            rol_id = data.pop("rol_id", None)
            orm = UsuarioORM(**data)
            orm.restaurante_id = self.restaurante_id
            if rol_id is not None:
                orm.rol_id = rol_id
            self.session.add(orm)
            await self.session.commit()
            await self.session.refresh(orm)
            return usuario_from_orm(orm)
        else:
            await self.session.execute(
                update(UsuarioORM)
                .where(
                    UsuarioORM.id == usuario.id,
                    UsuarioORM.restaurante_id == self.restaurante_id,
                )
                .values(
                    nombre_completo=usuario.nombre_completo,
                    username=usuario.username,
                    password_hash=usuario.password_hash,
                    activo=usuario.activo,
                    sesion_expira=usuario.sesion_expira,
                )
            )
            await self.session.commit()
            return await self.obtener_por_id(usuario.id)

    async def eliminar(self, usuario_id: int) -> None:
        q = select(UsuarioORM).where(
            UsuarioORM.id == usuario_id,
            UsuarioORM.restaurante_id == self.restaurante_id,
        )
        res = await self.session.execute(q)
        orm = res.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)
            await self.session.commit()

    async def actualizar_sesion(self, usuario_id: int, sesion_expira: datetime, ultimo_acceso: datetime) -> None:
        await self.session.execute(
            update(UsuarioORM)
            .where(
                UsuarioORM.id == usuario_id,
                UsuarioORM.restaurante_id == self.restaurante_id,
            )
            .values(sesion_expira=sesion_expira, ultimo_acceso=ultimo_acceso)
        )
        await self.session.commit()
