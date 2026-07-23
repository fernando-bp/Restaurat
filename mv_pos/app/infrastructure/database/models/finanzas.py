from __future__ import annotations

from datetime import date, datetime
from sqlalchemy import Boolean, Column, Date, DateTime, DECIMAL, ForeignKey, Integer, String
from app.infrastructure.database.base import Base


class GastoOperativoORM(Base):
    __tablename__ = "gastos_operativos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(Date, nullable=False, default=date.today)
    categoria = Column(String(80), nullable=False)
    monto = Column(DECIMAL(14, 2), nullable=False)
    descripcion = Column(String(500), nullable=True)
    es_recurrente = Column(Boolean, nullable=False, default=False)
    frecuencia = Column(String(20), nullable=True)  # mensual, semanal, etc.
    proxima_fecha = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class CompraProveedorORM(Base):
    __tablename__ = "compras_proveedores"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(Date, nullable=False, default=date.today)
    proveedor = Column(String(150), nullable=False)
    ingrediente_id = Column(Integer, ForeignKey("ingredientes.id"), nullable=True)
    descripcion = Column(String(300), nullable=False)
    cantidad = Column(DECIMAL(12, 4), nullable=False)
    unidad = Column(String(20), nullable=False, default="unidad")
    costo_total = Column(DECIMAL(14, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
