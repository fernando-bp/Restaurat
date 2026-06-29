from __future__ import annotations
from sqlalchemy import Column, Integer, ForeignKey, DECIMAL
from app.infrastructure.database.base import Base


class RecetaSubORM(Base):
    __tablename__ = "receta_sub"

    id = Column(Integer, primary_key=True, autoincrement=True)
    receta_padre_id = Column(Integer, ForeignKey("recetas.id"), nullable=False)
    receta_base_id = Column(Integer, ForeignKey("recetas.id"), nullable=False)
    cantidad_g = Column(DECIMAL(10, 4), nullable=False)

    class Config:
        from_attributes = True
