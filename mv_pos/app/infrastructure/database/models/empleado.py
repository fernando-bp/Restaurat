from __future__ import annotations
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL
from app.infrastructure.database.base import Base


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
