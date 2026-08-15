from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.config import settings
from app.infrastructure.storage import r2_storage

router = APIRouter(prefix="/media", tags=["media"])

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/gif", "image/webp"}


@router.post("/upload")
async def upload_image(file: UploadFile = File(...)) -> Any:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de archivo no permitido")

    content = await file.read()

    if settings.r2_enabled:
        try:
            url = await r2_storage.upload_image(content, file.filename, file.content_type)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"No se pudo subir la imagen: {exc}")
        return JSONResponse(content={"filename": file.filename, "url": url})

    # Fallback a disco local (desarrollo sin R2)
    media_root = Path(settings.media_root)
    if not media_root.is_absolute():
        media_root = Path(__file__).resolve().parents[5] / media_root
    media_root.mkdir(parents=True, exist_ok=True)
    destination = media_root / file.filename
    try:
        with destination.open("wb") as buffer:
            buffer.write(content)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar la imagen: {exc}")

    return JSONResponse(
        content={
            "filename": file.filename,
            "url": f"{settings.media_url}/{file.filename}",
            "saved_path": str(destination),
        }
    )
