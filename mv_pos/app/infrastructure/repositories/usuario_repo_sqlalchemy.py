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
    def __init__(self, session: AsyncSession):
        self.session = session

    async def obtener_por_id(self, usuario_id: int) -> Usuario | None:
        q = select(UsuarioORM).where(UsuarioORM.id == usuario_id)
        res = await self.session.execute(q)
        orm = res.scalar_one_or_none()
        return usuario_from_orm(orm)

    async def obtener_por_username(self, username: str) -> Usuario | None:
        q = select(UsuarioORM).where(UsuarioORM.username == username)
        res = await self.session.execute(q)
        orm = res.scalar_one_or_none()
        return usuario_from_orm(orm)

    async def obtener_por_email(self, email: str) -> Usuario | None:
        # Search in empleados.email linked to usuarios.usuario_id
        q = select(UsuarioORM).join(EmpleadoORM, EmpleadoORM.usuario_id == UsuarioORM.id).where(EmpleadoORM.email == email)
        res = await self.session.execute(q)
        orm = res.scalar_one_or_none()
        return usuario_from_orm(orm)

    async def listar(self) -> list[Usuario]:
        q = select(UsuarioORM)
        res = await self.session.execute(q)
        rows = res.scalars().all()
        return [usuario_from_orm(r) for r in rows]

    async def agregar(self, usuario: Usuario) -> Usuario:
        if usuario.id is None:
            data = orm_from_usuario(usuario)
            # remove id and rol_id None
            data.pop("id", None)
            rol_id = data.pop("rol_id", None)
            orm = UsuarioORM(**data)
            if rol_id is not None:
                orm.rol_id = rol_id
            self.session.add(orm)
            await self.session.commit()
            await self.session.refresh(orm)
            return usuario_from_orm(orm)
        else:
            # update existing
            await self.session.execute(
                update(UsuarioORM)
                .where(UsuarioORM.id == usuario.id)
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
        q = select(UsuarioORM).where(UsuarioORM.id == usuario_id)
        res = await self.session.execute(q)
        orm = res.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)
            await self.session.commit()

    async def actualizar_sesion(self, usuario_id: int, sesion_expira: datetime, ultimo_acceso: datetime) -> None:
        await self.session.execute(
            update(UsuarioORM)
            .where(UsuarioORM.id == usuario_id)
            .values(sesion_expira=sesion_expira, ultimo_acceso=ultimo_acceso)
        )
        await self.session.commit()
