from __future__ import annotations
from sqlalchemy import Column, Integer, ForeignKey, DECIMAL, String
from app.infrastructure.database.base import Base


class RecetaDetalleORM(Base):
    __tablename__ = "receta_detalle"

    id = Column(Integer, primary_key=True, autoincrement=True)
    receta_id = Column(Integer, ForeignKey("recetas.id"), nullable=False)
    ingrediente_id = Column(Integer, ForeignKey("ingredientes.id"), nullable=False)
    cantidad = Column(DECIMAL(10, 4), nullable=False)
    unidad_id = Column(Integer, ForeignKey("unidades_medida.id"), nullable=False)
    notas = Column(String(255), nullable=True)

    class Config:
        from_attributes = True
