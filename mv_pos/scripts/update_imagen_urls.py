"""
Actualiza imagen_url en la tabla recetas con las URLs de R2 generadas
por upload_to_r2_local.py (guardadas en r2_upload_results.json).

Uso:
    cd mv_pos
    python scripts/update_imagen_urls.py

El archivo r2_upload_results.json debe estar en la raíz del repositorio
(un nivel arriba de mv_pos/).
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.infrastructure.database.models.receta import RecetaORM

# ── CONEXION ──────────────────────────────────────────────────────────────────
# Mismo patrón que migrate_images_to_r2.py: convierte drivers síncronos al
# equivalente async antes de pasar la URL a create_async_engine.
_SYNC_TO_ASYNC_DRIVER = {
    "mysql": "mysql+aiomysql",
    "mysql+mysqldb": "mysql+aiomysql",
    "mysql+pymysql": "mysql+aiomysql",
    "postgresql": "postgresql+asyncpg",
    "postgresql+psycopg2": "postgresql+asyncpg",
    "postgres": "postgresql+asyncpg",
}


def _async_url(url: str) -> str:
    scheme = url.split("://")[0]
    replacement = _SYNC_TO_ASYNC_DRIVER.get(scheme)
    if replacement:
        return replacement + "://" + url.split("://", 1)[1]
    return url
# ─────────────────────────────────────────────────────────────────────────────


RESULTS_FILE = Path(__file__).resolve().parents[2] / "r2_upload_results.json"


async def update() -> None:
    if not RESULTS_FILE.exists():
        print(f"ERROR: no se encontró {RESULTS_FILE}")
        return

    with open(RESULTS_FILE, encoding="utf-8") as f:
        results: dict = json.load(f)

    # {receta_id (int): url (str)}
    url_map = {int(k): v["url"] for k, v in results.items()}
    print(f"URLs a aplicar: {len(url_map)} recetas")

    db_url = _async_url(settings.database_url)
    print(f"Conectando con: {db_url.split('@')[0].rsplit(':', 1)[0]}:***@{db_url.split('@', 1)[-1]}")
    engine = create_async_engine(db_url, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    actualizadas = 0
    no_encontradas = []

    async with Session() as db:
        result = await db.execute(
            select(RecetaORM).where(RecetaORM.id.in_(url_map.keys()))
        )
        recetas = result.scalars().all()

        encontradas_ids = {receta.id for receta in recetas}
        for rid in url_map:
            if rid not in encontradas_ids:
                no_encontradas.append(rid)

        for receta in recetas:
            receta.imagen_url = url_map[receta.id]
            actualizadas += 1
            print(f"  ✓ Receta {receta.id} → {receta.imagen_url}")

        await db.commit()

    await engine.dispose()

    if no_encontradas:
        print(f"\nIDs no encontrados en la BD: {no_encontradas}")

    print(f"\nActualizadas: {actualizadas} | No encontradas: {len(no_encontradas)}")


if __name__ == "__main__":
    asyncio.run(update())
