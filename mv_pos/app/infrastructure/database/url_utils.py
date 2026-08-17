from __future__ import annotations


def make_async_url(url: str) -> str:
    """
    CONCEPTO: SQLAlchemy necesita drivers *async* distintos al driver sync.

    - PostgreSQL sync:  postgresql://  → async: postgresql+asyncpg://
    - MySQL sync:       mysql://       → async: mysql+aiomysql://

    Railway y otras plataformas entregan URLs sync. Esta función las convierte
    automáticamente para que SQLAlchemy pueda usarlas con asyncio.

    Sin esto, verías: "Can't load plugin: sqlalchemy.dialects:postgresql"
    """
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("mysql://"):
        return url.replace("mysql://", "mysql+aiomysql://", 1)
    return url
