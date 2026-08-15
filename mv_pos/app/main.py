from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import inspect, text
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.presentation.api.v1.router import create_v1_router
from app.presentation.middlewares.cors_middleware import add_cors
from app.presentation.exception_handlers.http_exception_handler import register_exception_handlers
from app.infrastructure.database.connection import engine
from app.infrastructure.database.base import Base

app = FastAPI(
    title="MV-POS Magic Village",
    version="0.1.0",
    description="Backend MV-POS con Clean Architecture y FastAPI",
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
    """Endpoint used by Railway to confirm the HTTP service is running."""
    return {"status": "ok"}

@app.on_event("startup")
async def startup_event() -> None:
    """Inicializa recursos de la aplicación."""
    if not settings.r2_enabled:
        media_root.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        columns = {
            'reference_code': 'VARCHAR(100)',
            'cufe': 'VARCHAR(255)',
            'qr_url': 'VARCHAR(500)',
            'pdf_url': 'VARCHAR(500)',
            'intentos': 'INT DEFAULT 0',
            'ultimo_error': 'VARCHAR(1000)',
            'factus_response': 'JSON',
        }

        existing_columns = await conn.run_sync(
            lambda sync_conn: {column["name"] for column in inspect(sync_conn).get_columns("facturas")}
        )
        for name, definition in columns.items():
            if name not in existing_columns:
                await conn.execute(text(f"ALTER TABLE facturas ADD COLUMN {name} {definition}"))

@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Libera recursos al apagar la aplicación."""
    ...
