from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, DECIMAL, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from app.infrastructure.database.base import Base


class InventarioORM(Base):
    __tablename__ = "inventario"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ingrediente_id = Column(Integer, ForeignKey("ingredientes.id"), nullable=False, unique=True)
    stock_actual = Column(DECIMAL(12, 4), nullable=False, default=0.0000)
    stock_minimo = Column(DECIMAL(12, 4), nullable=False, default=0.0000)
    stock_maximo = Column(DECIMAL(12, 4), nullable=True)
    ubicacion = Column(String(60), nullable=True)
    ultima_actualizacion = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    ingrediente = relationship("IngredienteORM", lazy="joined")

    class Config:
        from_attributes = True
