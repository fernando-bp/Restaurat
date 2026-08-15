"""
Script de migración: mueve las imágenes de recetas almacenadas como BLOB
en la base de datos hacia Cloudflare R2.

Uso:
    cd mv_pos
    python scripts/migrate_images_to_r2.py

Requiere las variables de entorno de R2 configuradas en .env:
    R2_ENDPOINT_URL, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY,
    R2_BUCKET_NAME, R2_PUBLIC_URL
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.infrastructure.database.models.receta import RecetaORM
from app.infrastructure.storage import r2_storage

# Mapa de drivers síncronos → async equivalente
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


async def migrate() -> None:
    if not settings.r2_enabled:
        print("ERROR: R2 no está configurado. Verifica R2_ENDPOINT_URL, R2_ACCESS_KEY_ID y R2_BUCKET_NAME en .env")
        return

    db_url = _async_url(settings.database_url)
    print(f"Conectando con: {db_url.split('@')[0].rsplit(':', 1)[0]}:***@{db_url.split('@', 1)[-1]}")
    engine = create_async_engine(db_url, echo=False)
    Session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    migradas = 0
    errores = 0

    # Una sola sesión: carga, sube y actualiza sin cerrar entre pasos.
    # Crítico: los bytes del BLOB (asyncpg los devuelve como memoryview)
    # deben convertirse a bytes() mientras la sesión está abierta; si la
    # sesión se cierra antes de leerlos, el buffer queda inválido y se
    # obtiene basura (p.ej. el valor de created_at en lugar de la imagen).
    async with Session() as db:
        result = await db.execute(
            select(RecetaORM).where(
                RecetaORM.imagen.is_not(None),
                RecetaORM.imagen_url.is_(None),
            )
        )
        recetas = result.scalars().all()
        print(f"Encontradas {len(recetas)} recetas con imagen BLOB sin URL de R2.")

        for receta in recetas:
            # Convertir a bytes() aquí, dentro de la sesión activa,
            # antes de cualquier await que pueda invalidar el buffer.
            contenido: bytes = bytes(receta.imagen)
            mime: str = receta.imagen_tipo or "image/png"
            receta_id: int = receta.id
            nombre: str = receta.nombre

            try:
                ext = mime.split("/")[-1]
                url = await r2_storage.upload_image(contenido, f"receta_{receta_id}.{ext}", mime)

                receta.imagen_url = url
                receta.imagen = None
                receta.imagen_tipo = None

                migradas += 1
                print(f"  ✓ Receta {receta_id} ({nombre}) → {url}")
            except Exception as exc:
                errores += 1
                print(f"  ✗ Receta {receta_id} ({nombre}): {exc}")

        await db.commit()

    await engine.dispose()
    print(f"\nMigración completada: {migradas} migradas, {errores} errores.")


if __name__ == "__main__":
    asyncio.run(migrate())
