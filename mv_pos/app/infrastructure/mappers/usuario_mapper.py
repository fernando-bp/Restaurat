from __future__ import annotations
from typing import Optional

from app.domain.entities.usuario import Usuario
from app.domain.entities.rol import Rol
from app.infrastructure.database.models.usuario import UsuarioORM


def usuario_from_orm(model: Optional[UsuarioORM]) -> Optional[Usuario]:
    if model is None:
        return None

    rol = None
    if model.rol is not None:
        rol = Rol(
            id=model.rol.id,
            nombre=model.rol.nombre,
            permisos={},
            activo=model.rol.activo,
        )

    return Usuario(
        id=model.id,
        nombre_completo=model.nombre_completo,
        username=model.username,
        password_hash=model.password_hash,
        rol=rol,
        activo=bool(model.activo),
        sesion_expira=model.sesion_expira,
    )


def orm_from_usuario(u: Usuario) -> dict:
    return {
        "id": u.id,
        "nombre_completo": u.nombre_completo,
        "username": u.username,
        "password_hash": u.password_hash,
        "rol_id": getattr(u.rol, "id", None) if u.rol else None,
        "activo": u.activo,
        "sesion_expira": u.sesion_expira,
    }
