from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Time, ForeignKey, DECIMAL, Computed
from sqlalchemy.orm import relationship
from app.infrastructure.database.base import Base


class PagoORM(Base):
    """Modelo ORM para Pagos (RF-27 a RF-34)
    
    Registra cada pago o grupo de pagos por forma de pago para una orden.
    Soporta pago mixto: múltiples filas por orden (RF-31).
    """
    __tablename__ = "pagos"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_id = Column(Integer, ForeignKey("ordenes.id"), nullable=False)
    forma_pago = Column(String(20), nullable=False)  # efectivo, tarjeta_debito, tarjeta_credito, nequi, daviplata, pse, cortesia
    monto = Column(DECIMAL(12, 0), nullable=False)  # Monto pagado en esta transacción
    monto_recibido = Column(DECIMAL(12, 0))  # Solo para efectivo
    cambio_entregado = Column(DECIMAL(12, 0))  # Solo para efectivo
    referencia_datafono = Column(String(100))  # Obligatorio para tarjeta (RF-29)
    numero_comprobante = Column(String(100))  # Obligatorio para transferencia (RF-30)
    cajero_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relaciones
    orden = relationship("OrdenORM", backref="pagos")
    cajero = relationship("UsuarioORM", backref="pagos_registrados")

    class Config:
        from_attributes = True


class CierreCajaORM(Base):
    """Modelo ORM para Cierre de Caja Diario (RF-34)
    
    Resumen diario de todas las transacciones por forma de pago
    con cuadre y diferencia de efectivo.
    """
    __tablename__ = "cierre_caja"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    fecha = Column(Date, nullable=False, unique=True)  # YYYY-MM-DD
    cajero_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    autorizado_por = Column(Integer, ForeignKey("usuarios.id"))
    
    # Totales
    total_ventas = Column(DECIMAL(14, 0), nullable=False, default=0)
    total_efectivo_sistema = Column(DECIMAL(14, 0), nullable=False, default=0)
    total_efectivo_contado = Column(DECIMAL(14, 0), nullable=False, default=0)
    total_tarjeta = Column(DECIMAL(14, 0), nullable=False, default=0)
    total_transferencia = Column(DECIMAL(14, 0), nullable=False, default=0)
    total_cortesia = Column(DECIMAL(14, 0), nullable=False, default=0)
    total_descuentos = Column(DECIMAL(14, 0), nullable=False, default=0)
    
    # Diferencia (calculada: total_efectivo_contado - total_efectivo_sistema)
    diferencia_efectivo = Column(
        DECIMAL(14, 0),
        Computed("total_efectivo_contado - total_efectivo_sistema"),
    )
    
    # Observaciones y firma
    observaciones = Column(String(500))
    firmado_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relaciones
    cajero = relationship("UsuarioORM", foreign_keys=[cajero_id], backref="cierres_caja_registrados")
    autorizado = relationship("UsuarioORM", foreign_keys=[autorizado_por], backref="cierres_caja_autorizados")

    class Config:
        from_attributes = True


class DescuentoORM(Base):
    """Modelo ORM para Descuentos y Cortesías (RF-33)
    
    Descuentos > 10% requieren PIN de administrador.
    """
    __tablename__ = "descuentos"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    orden_id = Column(Integer, ForeignKey("ordenes.id"), nullable=False)
    porcentaje = Column(DECIMAL(5, 2), nullable=False)  # 0.01 a 100.00
    monto = Column(DECIMAL(12, 0), nullable=False)
    motivo = Column(String(200), nullable=False)
    autorizado_por = Column(Integer, ForeignKey("usuarios.id"))  # Requerido si > 10%
    requirio_pin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relaciones
    orden = relationship("OrdenORM", backref="descuentos")
    autorizado = relationship("UsuarioORM", backref="descuentos_autorizados")

    class Config:
        from_attributes = True
