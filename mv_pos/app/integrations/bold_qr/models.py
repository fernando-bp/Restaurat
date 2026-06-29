from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, DECIMAL, Integer, String, Text

from app.infrastructure.database.base import Base


class BoldPaymentIntentORM(Base):
    __tablename__ = "bold_payment_intents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_id = Column(Integer, nullable=False, index=True)
    mesa_id = Column(Integer, nullable=True, index=True)
    cajero_id = Column(Integer, nullable=True)
    monto = Column(DECIMAL(14, 0), nullable=False)
    moneda = Column(String(3), nullable=False, default="COP")
    referencia = Column(String(120), nullable=False, unique=True, index=True)
    bold_payment_id = Column(String(120), unique=True, index=True)
    estado = Column(String(20), nullable=False, default="PENDIENTE", index=True)
    metodo_pago = Column(String(30), nullable=False, default="QR_BREB")
    qr_payload = Column(Text)
    webhook_id = Column(String(120), unique=True, index=True)
    ultimo_error = Column(String(500))
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
