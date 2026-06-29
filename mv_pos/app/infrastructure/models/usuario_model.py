from __future__ import annotations
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
import datetime

from app.infrastructure.database import Base


class RoleORM(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=False)
    descripcion = Column(String(255))
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class UsuarioORM(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre_completo = Column(String(150), nullable=False)
    username = Column(String(50), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    ultimo_acceso = Column(DateTime)
    sesion_token = Column(String(255))
    sesion_expira = Column(DateTime)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    role = relationship("RoleORM", lazy="joined")


class EmpleadoORM(Base):
    __tablename__ = "empleados"
    id = Column(Integer, primary_key=True, autoincrement=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True)
    nombre = Column(String(150), nullable=False)
    cedula = Column(String(20), nullable=False)
    telefono = Column(String(20))
    email = Column(String(100))
    cargo = Column(String(80), nullable=False)
    fecha_ingreso = Column(DateTime)
    salario_base = Column(DECIMAL(12, 2))
    activo = Column(Boolean, nullable=False, default=True)
