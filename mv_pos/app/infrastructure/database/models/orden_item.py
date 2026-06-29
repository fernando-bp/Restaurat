from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DECIMAL, DateTime
from sqlalchemy.orm import relationship
from app.infrastructure.database.base import Base


class OrdenItemORM(Base):
    __tablename__ = "orden_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_id = Column(Integer, ForeignKey("ordenes.id"), nullable=False)
    receta_id = Column(Integer, ForeignKey("recetas.id"), nullable=False)
    cantidad = Column(Integer, nullable=False, default=1)
    precio_unitario = Column(DECIMAL(10, 0), nullable=False)
    estado = Column(String(20), nullable=False, default='pendiente')
    modificadores = Column(String(500), nullable=True)
    notas = Column(String(500), nullable=True)
    cocinero_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    hora_lista = Column(DateTime, nullable=True)
    motivo_cancelacion = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    orden = relationship("OrdenORM", back_populates="items", lazy="joined")

    class Config:
        from_attributes = True
