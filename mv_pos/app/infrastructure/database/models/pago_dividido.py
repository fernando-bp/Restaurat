from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, DECIMAL, Boolean
from sqlalchemy.orm import relationship
from app.infrastructure.database.base import Base


class PagoDivididoORM(Base):
    """Modelo ORM para Pagos Divididos
    
    Registra la división de una cuenta entre múltiples personas.
    Permite que cada persona pague su parte de forma independiente.
    """
    __tablename__ = "pagos_divididos"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_id = Column(Integer, ForeignKey("ordenes.id"), nullable=False)
    numero_personas = Column(Integer, nullable=False)  # Total de personas en la división
    monto_total = Column(DECIMAL(12, 0), nullable=False)  # Total de la cuenta
    
    # Control de ejecución
    completado = Column(Boolean, nullable=False, default=False)  # ¿Se completó la división?
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime)  # Cuándo se completó la división
    
    # Relaciones
    orden = relationship("OrdenORM")
    personas = relationship("PersonaPagoDivididoORM", back_populates="pago_dividido", cascade="all, delete-orphan")
    
    class Config:
        from_attributes = True


class PersonaPagoDivididoORM(Base):
    """Modelo ORM para personas en un pago dividido
    
    Cada persona tiene su monto asignado y estado de pago.
    """
    __tablename__ = "personas_pago_dividido"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pago_dividido_id = Column(Integer, ForeignKey("pagos_divididos.id"), nullable=False)
    numero_persona = Column(Integer, nullable=False)  # 1, 2, 3, ... N
    monto = Column(DECIMAL(12, 0), nullable=False)  # Monto que debe pagar esta persona
    
    # Estado del pago
    pagado = Column(Boolean, nullable=False, default=False)  # ¿Pagó?
    forma_pago = Column(String(20))  # efectivo, tarjeta_debito, tarjeta_credito, nequi, daviplata, pse, cortesia
    monto_recibido = Column(DECIMAL(12, 0))  # Solo para efectivo
    cambio_entregado = Column(DECIMAL(12, 0))  # Solo para efectivo
    referencia_datafono = Column(String(100))  # Para tarjeta
    numero_comprobante = Column(String(100))  # Para transferencia
    
    # Auditoría
    cajero_id = Column(Integer, ForeignKey("usuarios.id"))
    pagado_at = Column(DateTime)  # Cuándo se registró el pago
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relaciones
    pago_dividido = relationship("PagoDivididoORM", back_populates="personas")
    cajero = relationship("UsuarioORM", backref="personas_pago_dividido")
    
    class Config:
        from_attributes = True
