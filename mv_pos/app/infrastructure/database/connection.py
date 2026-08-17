from __future__ import annotations

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.config import settings
from app.infrastructure.database.url_utils import make_async_url

# CONCEPTO: Este engine es el "default" — apunta al DATABASE_URL del .env.
#
# En single-tenant (el estado actual): es el único engine y lo usan todos.
# En multi-tenant: sigue existiendo pero get_db_session lo ignora cuando
# hay un JWT con restaurante_id; en su lugar usa el engine del tenant_registry.
#
# Lo mantenemos para:
# 1. Backward compat (startup crea tablas aquí si no hay tenants configurados).
# 2. Rutas sin autenticación que necesiten un DB de fallback.

database_url = make_async_url(settings.database_url)

engine = create_async_engine(
    database_url,
    future=True,
    echo=False,
    pool_pre_ping=True,
)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
