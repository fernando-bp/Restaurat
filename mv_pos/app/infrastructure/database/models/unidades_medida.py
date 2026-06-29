from __future__ import annotations
from sqlalchemy import Column, Integer, String, Enum
from app.infrastructure.database.base import Base


class UnidadMedidaORM(Base):
    __tablename__ = "unidades_medida"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(50), nullable=False, unique=True)
    abreviatura = Column(String(10), nullable=False)
    tipo = Column(String(10), nullable=False)

    class Config:
        from_attributes = True
