from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.presentation.dependencies.db_deps import get_db_session
from app.infrastructure.repositories.ingrediente_repo_sqlalchemy import IngredienteRepoSQLAlchemy

ingrediente_router = APIRouter(prefix="/ingredientes", tags=["ingredientes"])


@ingrediente_router.get("/{ingrediente_id}", summary="Obtener ingrediente por id")
async def obtener_ingrediente(ingrediente_id: int, db: AsyncSession = Depends(get_db_session)) -> dict:
    # Allow public read of ingredient names to support POS UI lookups
    ingrediente_repo = IngredienteRepoSQLAlchemy(db)
    ingrediente = await ingrediente_repo.obtener_por_id(ingrediente_id)
    if ingrediente is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Ingrediente {ingrediente_id} no encontrado")
    return {"id": ingrediente.id, "nombre": ingrediente.nombre}
