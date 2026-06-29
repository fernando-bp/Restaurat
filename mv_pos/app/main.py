from pathlib import Path

from fastapi import FastAPI
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
media_root.mkdir(parents=True, exist_ok=True)
app.mount(settings.media_url, StaticFiles(directory=str(media_root)), name="media")

@app.on_event("startup")
async def startup_event() -> None:
    """Inicializa recursos de la aplicación."""
    media_root.mkdir(parents=True, exist_ok=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Libera recursos al apagar la aplicación."""
    ...
