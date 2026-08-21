from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import inspect, select, text

from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.presentation.api.v1.router import create_v1_router
from app.presentation.middlewares.cors_middleware import add_cors
from app.presentation.exception_handlers.http_exception_handler import register_exception_handlers

from app.infrastructure.database.connection import engine
from app.infrastructure.database.base import Base
from app.infrastructure.database.models.restaurante import RestauranteORM

app = FastAPI(
    title="MV-POS Magic Village",
    version="0.2.0",
    description="Backend MV-POS con Clean Architecture y soporte multi-tenant (shared DB)",
    docs_url="/docs",
    redoc_url="/redoc",
)

add_cors(app)
register_exception_handlers(app)
app.include_router(create_v1_router(), prefix="/api/v1")

media_root = Path(settings.media_root)
if not media_root.is_absolute():
    media_root = Path(__file__).resolve().parent.parent / media_root

if not settings.r2_enabled:
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount(settings.media_url, StaticFiles(directory=str(media_root)), name="media")


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event() -> None:
    """
    Arranque del sistema shared-DB multi-tenant.

    1. create_all crea todas las tablas (incluyendo restaurantes).
       Si ya existen, no hace nada — idempotente.

    2. Aplicamos ALTER TABLE para columnas agregadas después de la
       creación inicial (restaurante_id, imagen_url, etc.).

    3. Si no existe ningún restaurante, creamos uno "default" con id=1
       para que el sistema funcione sin configuración extra.
    """
    if not settings.r2_enabled:
        media_root.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        # ── 1. Crear/verificar todas las tablas ─────────────────────────────
        await conn.run_sync(Base.metadata.create_all)

        # ── 2. Columnas adicionales por migración ────────────────────────────
        factura_columns = {
            "reference_code": "VARCHAR(100)",
            "cufe": "VARCHAR(255)",
            "qr_url": "VARCHAR(500)",
            "pdf_url": "VARCHAR(500)",
            "intentos": "INT DEFAULT 0",
            "ultimo_error": "VARCHAR(1000)",
            "factus_response": "JSON",
        }
        existing_factura = await conn.run_sync(
            lambda sc: {c["name"] for c in inspect(sc).get_columns("facturas")}
        )
        for col, definition in factura_columns.items():
            if col not in existing_factura:
                await conn.execute(text(f"ALTER TABLE facturas ADD COLUMN {col} {definition}"))

        receta_columns = {"imagen_url": "TEXT"}
        existing_receta = await conn.run_sync(
            lambda sc: {c["name"] for c in inspect(sc).get_columns("recetas")}
        )
        for col, definition in receta_columns.items():
            if col not in existing_receta:
                await conn.execute(text(f"ALTER TABLE recetas ADD COLUMN {col} {definition}"))

        cierre_cols = {"fondo_inicial": "INT NOT NULL DEFAULT 0"}
        existing_cierre = await conn.run_sync(
            lambda sc: {c["name"] for c in inspect(sc).get_columns("cierre_caja")}
        )
        for col, definition in cierre_cols.items():
            if col not in existing_cierre:
                await conn.execute(text(f"ALTER TABLE cierre_caja ADD COLUMN {col} {definition}"))

        # restaurante_id en todas las tablas raíz (NULL DEFAULT 1 para filas previas)
        tenant_columns: dict[str, list[str]] = {
            "mesas":              ["restaurante_id INT NOT NULL DEFAULT 1"],
            "ordenes":            ["restaurante_id INT NOT NULL DEFAULT 1"],
            "usuarios":           ["restaurante_id INT NOT NULL DEFAULT 1"],
            "recetas":            ["restaurante_id INT NOT NULL DEFAULT 1"],
            "ingredientes":       ["restaurante_id INT NOT NULL DEFAULT 1"],
            "cierre_caja":        ["restaurante_id INT NOT NULL DEFAULT 1"],
            "gastos_operativos":  ["restaurante_id INT NOT NULL DEFAULT 1"],
            "compras_proveedores":["restaurante_id INT NOT NULL DEFAULT 1"],
        }
        for table, columns in tenant_columns.items():
            try:
                existing = await conn.run_sync(
                    lambda sc, t=table: {c["name"] for c in inspect(sc).get_columns(t)}
                )
                for col_def in columns:
                    col_name = col_def.split()[0]
                    if col_name not in existing:
                        await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col_def}"))
            except Exception:
                pass  # tabla puede no existir aún en primer arranque

    # ── 3. Crear/recrear vista v_mesas_estado ───────────────────────────────
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE OR REPLACE VIEW v_mesas_estado AS
            SELECT
                m.id,
                m.numero,
                m.capacidad,
                m.zona,
                m.estado,
                m.restaurante_id,
                o.id             AS orden_id,
                o.num_comensales,
                o.hora_apertura,
                u.nombre_completo AS mesero,
                o.total_neto
            FROM mesas m
            LEFT JOIN (
                SELECT * FROM ordenes
                WHERE estado IN ('abierta','en_preparacion','lista','en_espera_cuenta')
            ) o ON o.mesa_id = m.id
            LEFT JOIN usuarios u ON u.id = o.mesero_id
            WHERE m.activa = 1
        """))

    # ── 4. Poblar imagen_url en recetas desde Cloudflare R2 ─────────────────
    r2_image_urls: dict[int, str] = {
        1: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_1.jpg",
        2: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_2.jpg",
        3: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_3.jpg",
        4: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_4.webp",
        5: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_5.png",
        6: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_6.jpg",
        7: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_7.avif",
        8: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_8.jpg",
        9: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_9.jpg",
        10: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_10.jpg",
        11: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_11.jpg",
        12: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_12.png",
        13: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_13.png",
        14: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_14.jpg",
        15: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_15.jpg",
        16: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_16.jpg",
        17: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_17.jpg",
        18: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_18.jpg",
        20: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_20.jpg",
        21: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_21.jpg",
        22: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_22.jpg",
        23: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_23.jpg",
        24: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_24.jpg",
        25: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_25.jpg",
        26: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_26.jpg",
        27: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_27.jpg",
        28: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_28.jpg",
        29: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_29.jpg",
        30: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_30.jpg",
        31: "https://pub-aa6fcaef9d844760b36fd58dec4d190d.r2.dev/images/receta_31.jpg",
    }
    async with engine.begin() as conn:
        for receta_id, url in r2_image_urls.items():
            await conn.execute(
                text(
                    "UPDATE recetas SET imagen_url = :url "
                    "WHERE id = :id AND (imagen_url IS NULL OR imagen_url = '')"
                ),
                {"url": url, "id": receta_id},
            )

    # ── 5. Crear restaurante "default" si no existe ninguno ──────────────────
    async with engine.begin() as conn:
        result = await conn.execute(select(RestauranteORM.id).limit(1))
        if result.fetchone() is None:
            await conn.execute(
                RestauranteORM.__table__.insert().values(
                    slug="default",
                    nombre="Restaurante Principal",
                    r2_prefix="",
                    activo=True,
                )
            )
