from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from app.infrastructure.database.base import Base


class ComandaORM(Base):
    __tablename__ = "comandas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_id = Column(Integer, ForeignKey("ordenes.id"), nullable=False)
    mesa_id = Column(Integer, ForeignKey("mesas.id"), nullable=True)
    contenido = Column(Text, nullable=False)
    estado = Column(String(20), nullable=False, default='pending')
    file_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    printed_at = Column(DateTime, nullable=True)

    class Config:
        from_attributes = True
