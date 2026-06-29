from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, BigInteger, Integer, ForeignKey, String, DECIMAL, Text, DateTime
from app.infrastructure.database.base import Base


class MovimientosInventarioORM(Base):
    __tablename__ = "movimientos_inventario"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ingrediente_id = Column(Integer, ForeignKey("ingredientes.id"), nullable=False)
    tipo = Column(String(20), nullable=False)
    cantidad = Column(DECIMAL(12, 4), nullable=False)
    stock_resultante = Column(DECIMAL(12, 4), nullable=False)
    precio_unitario_snap = Column(DECIMAL(10, 4), nullable=True)
    proveedor_id = Column(Integer, nullable=True)
    numero_factura = Column(String(50), nullable=True)
    motivo = Column(Text, nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    referencia_orden = Column(Integer, ForeignKey("ordenes.id"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    class Config:
        from_attributes = True
