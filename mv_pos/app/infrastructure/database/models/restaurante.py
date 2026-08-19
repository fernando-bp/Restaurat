from __future__ import annotations

from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from app.infrastructure.database.base import Base


class RestauranteORM(Base):
    __tablename__ = "restaurantes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(50), nullable=False, unique=True)
    nombre = Column(String(150), nullable=False)
    r2_prefix = Column(String(150), nullable=False, default="")
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Credenciales Factus por restaurante (facturación electrónica Colombia)
    factus_enabled = Column(Boolean, nullable=False, default=False)
    factus_api_base_url = Column(String(255), nullable=True)
    factus_client_id = Column(String(255), nullable=True)
    factus_client_secret = Column(String(500), nullable=True)
    factus_username = Column(String(255), nullable=True)
    factus_password = Column(String(255), nullable=True)
    factus_numbering_range_id = Column(Integer, nullable=True)
    factus_customer_municipality_code = Column(String(20), nullable=True)
