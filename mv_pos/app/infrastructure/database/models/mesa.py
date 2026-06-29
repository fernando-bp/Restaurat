from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Time, ForeignKey, DECIMAL
from sqlalchemy.orm import relationship
from app.infrastructure.database.base import Base


class MesaORM(Base):
    __tablename__ = "mesas"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    numero = Column(String(10), nullable=False, unique=True)
    capacidad = Column(Integer, default=4)
    zona = Column(String(50))
    estado = Column(String(20), default='libre')  # libre, ocupada, reservada, en_espera_cuenta
    activa = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    class Config:
        from_attributes = True


class OrdenORM(Base):
    __tablename__ = "ordenes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    mesa_id = Column(Integer, ForeignKey("mesas.id"), nullable=False)
    mesero_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    num_comensales = Column(Integer, default=1)
    estado = Column(String(20), default='abierta')  # abierta, en_preparacion, lista, pagada, cancelada
    notas_generales = Column(String(500))
    hora_apertura = Column(DateTime, nullable=False, default=datetime.utcnow)
    hora_confirmacion = Column(DateTime)
    hora_cierre = Column(DateTime)
    total_bruto = Column(DECIMAL(12, 0), default=0)
    total_descuento = Column(DECIMAL(12, 0), default=0)
    total_iva = Column(DECIMAL(12, 0), default=0)
    total_neto = Column(DECIMAL(12, 0), default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    mesa = relationship("MesaORM", lazy="joined")
    mesero = relationship("UsuarioORM", lazy="joined")
    items = relationship(
        "OrdenItemORM",
        back_populates="orden",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    pagos_divididos = relationship(
        "PagoDivididoORM",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

    class Config:
        from_attributes = True


class ReservaORM(Base):
    __tablename__ = "reservas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mesa_id = Column(Integer, ForeignKey("mesas.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    nombre_cliente = Column(String(150), nullable=False)
    telefono_cliente = Column(String(20), nullable=False)
    fecha_reserva = Column(Date, nullable=False)
    hora_reserva = Column(Time, nullable=False)
    num_personas = Column(Integer, default=1)
    notas = Column(String(500))
    estado = Column(String(20), default='activa')
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    mesa = relationship("MesaORM", lazy="joined")
    usuario = relationship("UsuarioORM", lazy="joined")

    class Config:
        from_attributes = True
