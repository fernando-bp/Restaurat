from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, DECIMAL, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.infrastructure.database.base import Base


class FacturaORM(Base):
    __tablename__ = "facturas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_id = Column(Integer, ForeignKey("ordenes.id"), nullable=False)
    cliente_nombre = Column(String(200), nullable=True)
    cliente_nit = Column(String(50), nullable=True)
    cliente_email = Column(String(200), nullable=True)
    numero_documento = Column(String(100), nullable=True)
    estado = Column(String(30), nullable=False, default="borrador")
    fecha_emision = Column(DateTime, nullable=False, default=datetime.utcnow)
    total_bruto = Column(DECIMAL(12, 0), nullable=False, default=0)
    total_descuento = Column(DECIMAL(12, 0), nullable=False, default=0)
    total_iva = Column(DECIMAL(12, 0), nullable=False, default=0)
    total_neto = Column(DECIMAL(12, 0), nullable=False, default=0)
    xml_documento = Column(Text, nullable=True)
    url_documento = Column(String(500), nullable=True)
    reference_code = Column(String(100), nullable=True)
    cufe = Column(String(255), nullable=True)
    qr_url = Column(String(500), nullable=True)
    pdf_url = Column(String(500), nullable=True)
    intentos = Column(Integer, nullable=False, default=0)
    ultimo_error = Column(String(1000), nullable=True)
    factus_response = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    orden = relationship("OrdenORM", lazy="joined")

    class Config:
        from_attributes = True
