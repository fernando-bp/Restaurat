from __future__ import annotations
import base64
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.infrastructure.storage import r2_storage
from app.presentation.dependencies.db_deps import get_db_session
from app.presentation.dependencies.auth_deps import get_current_user
from app.infrastructure.repositories.receta_repo_sqlalchemy import RecetaRepoSQLAlchemy
from app.application.dtos.receta_dto import (
    RecetaDetalleDTO,
    RecetaIngredienteDTO,
    RecetaListItemDTO,
    RecetaSubDetalleDTO,
    RecetaUpdateDTO,
)
from app.domain.enums.tipo_receta import TipoRecetaEnum
from app.infrastructure.database.models.ingrediente import IngredienteORM
from app.infrastructure.database.models.inventario import InventarioORM
from app.infrastructure.database.models.receta import RecetaORM
from app.infrastructure.database.models.receta_detalle import RecetaDetalleORM
from app.infrastructure.database.models.receta_sub import RecetaSubORM
from app.infrastructure.database.models.unidades_medida import UnidadMedidaORM

receta_router = APIRouter(prefix="/recetas", tags=["recetas"])
MYSQL_INT_MAX = 2_147_483_647
CATEGORIAS_MENU_VALIDAS = {
    "desayuno",
    "entrada",
    "fuerte",
    "pizza",
    "pasta",
    "hamburguesa",
    "al_horno",
    "bebida",
    "licor",
    "postre",
    "otro",
}
CATEGORIAS_MENU_ALIAS = {
    "sin categoria": "otro",
    "sin categoría": "otro",
    "salsas": "otro",
    "platos fuertes": "fuerte",
    "plato fuerte": "fuerte",
    "fuertes": "fuerte",
    "al horno": "al_horno",
    "bebidas": "bebida",
    "licores": "licor",
    "postres": "postre",
}


def _es_id_persistido(valor: int | None) -> bool:
    return isinstance(valor, int) and 0 < valor <= MYSQL_INT_MAX


def _categoria_menu_valida(categoria: str | None) -> str | None:
    if not categoria:
        return None
    normalizada = categoria.strip().lower()
    normalizada = CATEGORIAS_MENU_ALIAS.get(normalizada, normalizada)
    if normalizada in CATEGORIAS_MENU_VALIDAS:
        return normalizada
    return "otro"


def _imagen_a_data_url(receta: RecetaORM) -> str | None:
    if receta.imagen_url:
        return receta.imagen_url
    if not receta.imagen:
        return None
    mime = receta.imagen_tipo or "image/png"
    return f"data:{mime};base64,{base64.b64encode(receta.imagen).decode()}"


def _extraer_payload_base64(imagen_base64: str) -> tuple[bytes, str]:
    header = ""
    payload = imagen_base64
    if "," in imagen_base64:
        header, payload = imagen_base64.split(",", 1)
    mime = "image/png"
    if header.startswith("data:") and ";base64" in header:
        mime = header[5:].split(";base64", 1)[0] or "image/png"
    return base64.b64decode(payload), mime


async def _aplicar_imagen_receta(receta: RecetaORM, imagen_base64: str | None) -> None:
    if imagen_base64 == "":
        if receta.imagen_url and settings.r2_enabled:
            await r2_storage.delete_image(receta.imagen_url)
        receta.imagen = None
        receta.imagen_tipo = None
        receta.imagen_url = None
        return

    if not imagen_base64:
        return

    content, mime = _extraer_payload_base64(imagen_base64)

    if settings.r2_enabled:
        ext = mime.split("/")[-1]
        url = await r2_storage.upload_image(content, f"receta.{ext}", mime)
        if receta.imagen_url:
            await r2_storage.delete_image(receta.imagen_url)
        receta.imagen_url = url
        receta.imagen = None
        receta.imagen_tipo = None
    else:
        receta.imagen = content
        receta.imagen_tipo = mime
        receta.imagen_url = None


def _precio_venta_valido(request: RecetaUpdateDTO) -> int | None:
    if request.precio_venta is not None:
        return request.precio_venta
    if request.tipo == TipoRecetaEnum.FINAL.value:
        return 1
    return None


async def _serializar_ingredientes(db: AsyncSession, receta_id: int) -> List[RecetaIngredienteDTO]:
    result = await db.execute(
        select(RecetaDetalleORM, IngredienteORM, UnidadMedidaORM)
        .join(IngredienteORM, IngredienteORM.id == RecetaDetalleORM.ingrediente_id)
        .join(UnidadMedidaORM, UnidadMedidaORM.id == RecetaDetalleORM.unidad_id)
        .where(RecetaDetalleORM.receta_id == receta_id)
    )
    ingredientes: List[RecetaIngredienteDTO] = []
    for detalle, ingrediente, unidad in result.all():
        cantidad = float(detalle.cantidad)
        costo_unitario = float(ingrediente.precio_unitario)
        ingredientes.append(
            RecetaIngredienteDTO(
                ingrediente_id=int(ingrediente.id),
                nombre=ingrediente.nombre,
                cantidad=cantidad,
                unidad_id=int(unidad.id),
                unidad=unidad.abreviatura,
                costo_unitario=costo_unitario,
                costo_total=cantidad * costo_unitario,
                notas=detalle.notas,
            )
        )
    return ingredientes


async def _serializar_sub_recetas(
    db: AsyncSession,
    receta_id: int,
    visitadas: set[int] | None = None,
) -> List[RecetaSubDetalleDTO]:
    visitadas = visitadas or set()
    if receta_id in visitadas:
        return []
    visitadas.add(receta_id)

    result = await db.execute(
        select(RecetaSubORM, RecetaORM)
        .join(RecetaORM, RecetaORM.id == RecetaSubORM.receta_base_id)
        .where(RecetaSubORM.receta_padre_id == receta_id)
    )
    sub_recetas: List[RecetaSubDetalleDTO] = []
    for sub, receta_base in result.all():
        base_id = int(receta_base.id)
        sub_recetas.append(
            RecetaSubDetalleDTO(
                receta_base_id=base_id,
                nombre=receta_base.nombre,
                cantidad_g=float(sub.cantidad_g),
                ingredientes=await _serializar_ingredientes(db, base_id),
                sub_recetas=await _serializar_sub_recetas(db, base_id, set(visitadas)),
            )
        )
    return sub_recetas


async def _serializar_receta(db: AsyncSession, receta: RecetaORM) -> RecetaDetalleDTO:
    return RecetaDetalleDTO(
        id=int(receta.id),
        nombre=receta.nombre,
        tipo=receta.tipo,
        numero_receta=receta.numero_receta,
        pax=int(receta.pax or 1),
        peso_porcion_g=float(receta.peso_porcion_g) if receta.peso_porcion_g is not None else None,
        tiempo_prep_min=receta.tiempo_prep_min,
        precio_venta=int(receta.precio_venta) if receta.precio_venta is not None else None,
        categoria_menu=receta.categoria_menu,
        activa=bool(receta.activa),
        imagen_base64=_imagen_a_data_url(receta),
        ingredientes=await _serializar_ingredientes(db, int(receta.id)),
        sub_recetas=await _serializar_sub_recetas(db, int(receta.id)),
    )


async def _resolver_ingrediente(db: AsyncSession, ingrediente: RecetaIngredienteDTO, restaurante_id: int) -> int:
    ingrediente_orm = None
    if _es_id_persistido(ingrediente.ingrediente_id):
        result = await db.execute(
            select(IngredienteORM).where(
                IngredienteORM.id == ingrediente.ingrediente_id,
                IngredienteORM.restaurante_id == restaurante_id,
            )
        )
        ingrediente_orm = result.scalar_one_or_none()
    if ingrediente_orm is None and ingrediente.nombre:
        result = await db.execute(
            select(IngredienteORM).where(
                IngredienteORM.nombre == ingrediente.nombre,
                IngredienteORM.restaurante_id == restaurante_id,
            )
        )
        ingrediente_orm = result.scalar_one_or_none()
    if ingrediente_orm is None:
        ingrediente_orm = IngredienteORM(
            restaurante_id=restaurante_id,
            nombre=ingrediente.nombre or "Ingrediente sin nombre",
            unidad_base_id=ingrediente.unidad_id,
            precio_unitario=ingrediente.costo_unitario or 0,
            activo=True,
        )
        db.add(ingrediente_orm)
        await db.flush()
        db.add(InventarioORM(
            ingrediente_id=int(ingrediente_orm.id),
            stock_actual=0,
            stock_minimo=0,
        ))
        return int(ingrediente_orm.id)

    if ingrediente.nombre:
        ingrediente_orm.nombre = ingrediente.nombre
    if ingrediente.costo_unitario is not None:
        ingrediente_orm.precio_unitario = ingrediente.costo_unitario
    return int(ingrediente_orm.id)


async def _guardar_ingredientes_receta(
    db: AsyncSession,
    receta_id: int,
    ingredientes: List[RecetaIngredienteDTO],
    restaurante_id: int = 1,
) -> None:
    await db.execute(delete(RecetaDetalleORM).where(RecetaDetalleORM.receta_id == receta_id))
    for ingrediente in ingredientes:
        ingrediente_id = await _resolver_ingrediente(db, ingrediente, restaurante_id)
        db.add(
            RecetaDetalleORM(
                receta_id=receta_id,
                ingrediente_id=ingrediente_id,
                cantidad=ingrediente.cantidad,
                unidad_id=ingrediente.unidad_id,
                notas=ingrediente.notas,
            )
        )


async def _resolver_receta_base(db: AsyncSession, sub_receta: RecetaSubDetalleDTO, restaurante_id: int) -> int:
    receta = None
    if _es_id_persistido(sub_receta.receta_base_id):
        result = await db.execute(
            select(RecetaORM).where(
                RecetaORM.id == sub_receta.receta_base_id,
                RecetaORM.restaurante_id == restaurante_id,
            )
        )
        receta = result.scalar_one_or_none()
    if receta is None and sub_receta.nombre:
        result = await db.execute(
            select(RecetaORM).where(
                RecetaORM.nombre == sub_receta.nombre,
                RecetaORM.restaurante_id == restaurante_id,
            )
        )
        receta = result.scalar_one_or_none()
    if receta is None:
        receta = RecetaORM(
            restaurante_id=restaurante_id,
            nombre=sub_receta.nombre or "Subreceta sin nombre",
            tipo=TipoRecetaEnum.BASE.value,
            pax=1,
            activa=True,
        )
        db.add(receta)
        await db.flush()
        return int(receta.id)

    if receta.tipo != TipoRecetaEnum.BASE.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La receta usada como subreceta debe ser de tipo base.",
        )
    if sub_receta.nombre:
        receta.nombre = sub_receta.nombre
    return int(receta.id)


async def _guardar_sub_recetas_receta(
    db: AsyncSession,
    receta_id: int,
    sub_recetas: List[RecetaSubDetalleDTO],
    visitadas: set[int] | None = None,
    restaurante_id: int = 1,
) -> None:
    visitadas = visitadas or set()
    if receta_id in visitadas:
        return
    visitadas.add(receta_id)

    await db.execute(delete(RecetaSubORM).where(RecetaSubORM.receta_padre_id == receta_id))
    for sub_receta in sub_recetas:
        receta_base_id = await _resolver_receta_base(db, sub_receta, restaurante_id)
        db.add(
            RecetaSubORM(
                receta_padre_id=receta_id,
                receta_base_id=receta_base_id,
                cantidad_g=sub_receta.cantidad_g,
            )
        )
        await _guardar_ingredientes_receta(db, receta_base_id, sub_receta.ingredientes, restaurante_id)
        await _guardar_sub_recetas_receta(
            db,
            receta_base_id,
            sub_receta.sub_recetas,
            set(visitadas),
            restaurante_id,
        )


@receta_router.get(
    "/",
    response_model=List[RecetaListItemDTO],
    summary="Listar recetas finales activas",
    description="Devuelve las recetas de menú activas de tipo final.",
)
async def listar_recetas(
    activa: bool = True,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> List[RecetaListItemDTO]:
    receta_repo = RecetaRepoSQLAlchemy(db, current_user["restaurante_id"])
    recetas = await receta_repo.listar(activa=activa)
    return [
        RecetaListItemDTO(
            id=receta.id,
            nombre=receta.nombre,
            precio_venta=receta.precio_venta,
            categoria_menu=receta.categoria_menu,
            activa=receta.activa,
            imagen_base64=_imagen_a_data_url(receta),
        )
        for receta in recetas
        if receta.tipo == TipoRecetaEnum.FINAL
    ]


@receta_router.get(
    "/ingredientes",
    summary="Listar ingredientes disponibles para el recetario",
)
async def listar_ingredientes_catalogo(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    result = await db.execute(
        select(IngredienteORM, UnidadMedidaORM)
        .join(UnidadMedidaORM, UnidadMedidaORM.id == IngredienteORM.unidad_base_id)
        .where(
            IngredienteORM.activo.is_(True),
            IngredienteORM.restaurante_id == current_user["restaurante_id"],
        )
        .order_by(IngredienteORM.nombre)
    )
    return [
        {
            "id": int(ingrediente.id),
            "nombre": ingrediente.nombre,
            "unidad_id": int(unidad.id),
            "unidad": unidad.abreviatura,
            "costo_unitario": float(ingrediente.precio_unitario),
        }
        for ingrediente, unidad in result.all()
    ]


@receta_router.get(
    "/subrecetas",
    summary="Listar subrecetas disponibles para reutilizar",
)
async def listar_subrecetas_catalogo(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[dict]:
    result = await db.execute(
        select(RecetaORM)
        .where(
            RecetaORM.tipo == TipoRecetaEnum.BASE.value,
            RecetaORM.activa.is_(True),
            RecetaORM.restaurante_id == current_user["restaurante_id"],
        )
        .order_by(RecetaORM.nombre)
    )
    return [{"id": int(receta.id), "nombre": receta.nombre, "pax": int(receta.pax or 1)} for receta in result.scalars().all()]


@receta_router.post(
    "/",
    response_model=RecetaDetalleDTO,
    status_code=201,
    summary="Crear receta",
)
async def crear_receta(
    request: RecetaUpdateDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> RecetaDetalleDTO:
    receta = RecetaORM(
        restaurante_id=current_user["restaurante_id"],
        nombre=request.nombre,
        tipo=request.tipo,
        numero_receta=request.numero_receta,
        pax=request.pax,
        peso_porcion_g=request.peso_porcion_g,
        tiempo_prep_min=request.tiempo_prep_min,
        precio_venta=_precio_venta_valido(request),
        categoria_menu=_categoria_menu_valida(request.categoria_menu),
        activa=request.activa,
    )
    await _aplicar_imagen_receta(receta, request.imagen_base64)
    db.add(receta)
    await db.flush()

    rid = current_user["restaurante_id"]
    await _guardar_ingredientes_receta(db, int(receta.id), request.ingredientes, rid)
    await _guardar_sub_recetas_receta(db, int(receta.id), request.sub_recetas, restaurante_id=rid)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo crear la receta. Revisa que el nombre, numero de receta, ingredientes y subrecetas no esten duplicados.",
        ) from exc
    await db.refresh(receta)
    return await _serializar_receta(db, receta)


@receta_router.get(
    "/{receta_id}",
    response_model=RecetaDetalleDTO,
    summary="Obtener receta con ingredientes y subrecetas",
)
async def obtener_receta(
    receta_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> RecetaDetalleDTO:
    result = await db.execute(
        select(RecetaORM).where(
            RecetaORM.id == receta_id,
            RecetaORM.restaurante_id == current_user["restaurante_id"],
        )
    )
    receta = result.scalar_one_or_none()
    if receta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")
    return await _serializar_receta(db, receta)


@receta_router.put(
    "/{receta_id}",
    response_model=RecetaDetalleDTO,
    summary="Actualizar receta, ingredientes y subrecetas",
)
async def actualizar_receta(
    receta_id: int,
    request: RecetaUpdateDTO,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> RecetaDetalleDTO:
    result = await db.execute(
        select(RecetaORM).where(
            RecetaORM.id == receta_id,
            RecetaORM.restaurante_id == current_user["restaurante_id"],
        )
    )
    receta = result.scalar_one_or_none()
    if receta is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Receta no encontrada")

    receta.nombre = request.nombre
    receta.tipo = request.tipo
    receta.numero_receta = request.numero_receta
    receta.pax = request.pax
    receta.peso_porcion_g = request.peso_porcion_g
    receta.tiempo_prep_min = request.tiempo_prep_min
    receta.precio_venta = _precio_venta_valido(request)
    receta.categoria_menu = _categoria_menu_valida(request.categoria_menu)
    receta.activa = request.activa
    await _aplicar_imagen_receta(receta, request.imagen_base64)

    rid = current_user["restaurante_id"]
    await _guardar_ingredientes_receta(db, receta_id, request.ingredientes, rid)
    await _guardar_sub_recetas_receta(db, receta_id, request.sub_recetas, restaurante_id=rid)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No se pudo actualizar la receta. Revisa que el nombre, numero de receta, ingredientes y subrecetas no esten duplicados.",
        ) from exc
    await db.refresh(receta)
    return await _serializar_receta(db, receta)
