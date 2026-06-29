from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DECIMAL, DateTime, LargeBinary
from app.infrastructure.database.base import Base


class RecetaORM(Base):
    __tablename__ = "recetas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), nullable=False)
    tipo = Column(String(50), nullable=False)
    numero_receta = Column(String(50), nullable=True)
    pax = Column(Integer, default=1)
    peso_porcion_g = Column(DECIMAL(12, 2), nullable=True)
    tiempo_prep_min = Column(Integer, nullable=True)
    precio_venta = Column(Integer, nullable=True)
    categoria_menu = Column(String(100), nullable=True)
    activa = Column(Boolean, default=True)
    imagen = Column(LargeBinary, nullable=True)
    imagen_tipo = Column(String(100), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
