from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.infrastructure.database.base import Base


class UsuarioORM(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        UniqueConstraint("restaurante_id", "username", name="uq_usuario_restaurante_username"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    restaurante_id = Column(Integer, nullable=False, default=1)
    nombre_completo = Column(String(150), nullable=False)
    username = Column(String(50), nullable=False)
    password_hash = Column(String(255), nullable=False)
    rol_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    ultimo_acceso = Column(DateTime)
    sesion_token = Column(String(255))
    sesion_expira = Column(DateTime)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    rol = relationship("RolORM", lazy="joined")
