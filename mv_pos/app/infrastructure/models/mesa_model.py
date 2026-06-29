from __future__ import annotations
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, DECIMAL
import datetime

from app.infrastructure.database import Base


class MesaORM(Base):
    __tablename__ = "mesas"
    id = Column(Integer, primary_key=True, autoincrement=True)
    numero = Column(String(10), nullable=False, unique=True)
    capacidad = Column(Integer, default=4)
    zona = Column(String(50))
    estado = Column(String(20), default='libre')
    activa = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    class Config:
        from_attributes = True


class OrdenORM(Base):
    __tablename__ = "ordenes"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mesa_id = Column(Integer, ForeignKey("mesas.id"), nullable=False)
    mesero_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    num_comensales = Column(Integer, default=1)
    estado = Column(String(20), default='abierta')
    notas_generales = Column(String(500))
    hora_apertura = Column(DateTime, default=datetime.datetime.utcnow)
    hora_confirmacion = Column(DateTime)
    hora_cierre = Column(DateTime)
    total_bruto = Column(DECIMAL(12, 0), default=0)
    total_descuento = Column(DECIMAL(12, 0), default=0)
    total_iva = Column(DECIMAL(12, 0), default=0)
    total_neto = Column(DECIMAL(12, 0), default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    class Config:
        from_attributes = True
