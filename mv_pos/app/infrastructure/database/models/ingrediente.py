from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from app.infrastructure.database.base import Base


class IngredienteORM(Base):
    __tablename__ = "ingredientes"
    __table_args__ = (
        UniqueConstraint("restaurante_id", "nombre", name="uq_ingrediente_restaurante_nombre"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    restaurante_id = Column(Integer, nullable=False, default=1)
    nombre = Column(String(150), nullable=False)
    unidad_base_id = Column(Integer, ForeignKey("unidades_medida.id"), nullable=False)
    precio_unitario = Column(DECIMAL(10, 4), nullable=False)
    categoria = Column(String(60), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    unidad = relationship("UnidadMedidaORM", lazy="joined")

    class Config:
        from_attributes = True
