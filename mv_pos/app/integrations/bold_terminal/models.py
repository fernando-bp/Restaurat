from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, DateTime, DECIMAL, Integer, String, Text
from app.infrastructure.database.base import Base


class BoldTerminalPaymentORM(Base):
    __tablename__ = "bold_terminal_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_id = Column(Integer, nullable=False, index=True)
    mesa_id = Column(Integer, nullable=False)
    cajero_id = Column(Integer, nullable=False)
    monto = Column(DECIMAL(14, 0), nullable=False)
    referencia = Column(String(120), unique=True, nullable=False, index=True)
    integration_id = Column(String(120), unique=True, nullable=True, index=True)
    terminal_model = Column(String(50), nullable=False)
    terminal_serial = Column(String(100), nullable=False)
    estado = Column(String(20), nullable=False, default="PENDIENTE", index=True)
    webhook_id = Column(String(120), unique=True, nullable=True, index=True)
    payment_id = Column(String(120), unique=True, nullable=True, index=True)
    referencia_datafono = Column(String(120), nullable=True)
    ultimo_error = Column(String(500), nullable=True)
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
