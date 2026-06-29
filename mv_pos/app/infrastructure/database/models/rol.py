from __future__ import annotations
from sqlalchemy import Column, Integer, String, Boolean, Text
from app.infrastructure.database.base import Base


class RolORM(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=False, unique=True)
    descripcion = Column(Text)
    activo = Column(Boolean, nullable=False, default=True)
