from __future__ import annotations

import unicodedata

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.receta import Receta
from app.domain.entities.receta_detalle import RecetaDetalle
from app.domain.entities.receta_sub import RecetaSub
from app.domain.enums.tipo_receta import TipoRecetaEnum
from app.domain.repositories.receta_repository import RecetaRepository
from app.infrastructure.database.models.ingrediente import IngredienteORM
from app.infrastructure.database.models.receta import RecetaORM
from app.infrastructure.database.models.receta_detalle import RecetaDetalleORM
from app.infrastructure.database.models.receta_sub import RecetaSubORM
from app.infrastructure.database.models.unidades_medida import UnidadMedidaORM


_UNIT_FACTORS = {
    "mg": ("peso", 0.001),
    "miligramo": ("peso", 0.001),
    "miligramos": ("peso", 0.001),
    "g": ("peso", 1.0),
    "gr": ("peso", 1.0),
    "gramo": ("peso", 1.0),
    "gramos": ("peso", 1.0),
    "kg": ("peso", 1000.0),
    "kilo": ("peso", 1000.0),
    "kilos": ("peso", 1000.0),
    "kilogramo": ("peso", 1000.0),
    "kilogramos": ("peso", 1000.0),
    "lb": ("peso", 453.59237),
    "libra": ("peso", 453.59237),
    "libras": ("peso", 453.59237),
    "oz": ("peso", 28.349523125),
    "onza": ("peso", 28.349523125),
    "onzas": ("peso", 28.349523125),
    "ml": ("volumen", 1.0),
    "cc": ("volumen", 1.0),
    "cm3": ("volumen", 1.0),
    "l": ("volumen", 1000.0),
    "lt": ("volumen", 1000.0),
    "lts": ("volumen", 1000.0),
    "litro": ("volumen", 1000.0),
    "litros": ("volumen", 1000.0),
    "u": ("unidad", 1.0),
    "un": ("unidad", 1.0),
    "und": ("unidad", 1.0),
    "unidad": ("unidad", 1.0),
    "unidades": ("unidad", 1.0),
    "docena": ("unidad", 12.0),
    "docenas": ("unidad", 12.0),
    "tajada": ("unidad", 1.0),
    "tajadas": ("unidad", 1.0),
    "lamina": ("unidad", 1.0),
    "laminas": ("unidad", 1.0),
}


class RecetaRepoSQLAlchemy(RecetaRepository):

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def obtener_por_id(self, receta_id: int) -> Receta | None:
        receta = await self._cargar_receta_completa(receta_id)
        return receta

    async def listar(self, activa: bool | None = None) -> list[Receta]:
        query = select(RecetaORM)
        if activa is not None:
            query = query.where(RecetaORM.activa == activa)
        result = await self.session.execute(query)
        recetas = result.scalars().all()
        return [
            Receta(
                id=receta.id,
                nombre=receta.nombre,
                tipo=TipoRecetaEnum(receta.tipo),
                numero_receta=receta.numero_receta,
                pax=receta.pax,
                peso_porcion_g=float(receta.peso_porcion_g) if receta.peso_porcion_g is not None else None,
                tiempo_prep_min=receta.tiempo_prep_min,
                precio_venta=int(receta.precio_venta) if receta.precio_venta is not None else None,
                categoria_menu=receta.categoria_menu,
                activa=receta.activa,
                ingredientes=[],
                sub_recetas=[],
                imagen=receta.imagen,
                imagen_tipo=receta.imagen_tipo,
            )
            for receta in recetas
        ]

    async def guardar(self, receta: Receta) -> Receta:
        receta_orm = RecetaORM(
            id=receta.id,
            nombre=receta.nombre,
            tipo=receta.tipo,
            numero_receta=receta.numero_receta,
            pax=receta.pax,
            peso_porcion_g=receta.peso_porcion_g,
            tiempo_prep_min=receta.tiempo_prep_min,
            precio_venta=receta.precio_venta,
            categoria_menu=receta.categoria_menu,
            activa=receta.activa,
            imagen=receta.imagen,
            imagen_tipo=receta.imagen_tipo,
        )
        self.session.add(receta_orm)
        await self.session.flush()
        receta.id = receta_orm.id
        return receta

    async def eliminar(self, receta_id: int) -> None:
        result = await self.session.execute(select(RecetaORM).where(RecetaORM.id == receta_id))
        receta_orm = result.scalar_one_or_none()
        if receta_orm is not None:
            await self.session.delete(receta_orm)
            await self.session.flush()

    async def explotar_bom(self, receta_id: int, porciones: int) -> dict[int, float]:
        acumulado: dict[int, float] = {}
        cache: dict[int, Receta] = {}
        unit_cache: dict[int, UnidadMedidaORM] = {}
        ingredient_unit_cache: dict[int, int] = {}
        yield_cache: dict[int, float] = {}

        async def _expandir(receta_id_inner: int, factor: float) -> None:
            receta = await self._cargar_receta_en_cache(receta_id_inner, cache)
            for detalle in receta.ingredientes:
                cantidad_base = await self._convertir_a_unidad_base(
                    cantidad=detalle.cantidad,
                    unidad_origen_id=detalle.unidad_id,
                    ingrediente_id=detalle.ingrediente_id,
                    unit_cache=unit_cache,
                    ingredient_unit_cache=ingredient_unit_cache,
                )
                cantidad_total = cantidad_base * factor
                acumulado[detalle.ingrediente_id] = acumulado.get(detalle.ingrediente_id, 0.0) + float(cantidad_total)

            for sub in receta.sub_recetas:
                sub_receta = await self._cargar_receta_en_cache(sub.receta_base_id, cache)
                denominador = await self._obtener_rendimiento_sub_receta(sub_receta, unit_cache, yield_cache)
                factor_sub = factor * (float(sub.cantidad_g) / (denominador if denominador != 0 else 1))
                await _expandir(sub.receta_base_id, factor_sub)

        await _expandir(receta_id, float(porciones))
        return acumulado

    async def _obtener_rendimiento_sub_receta(
        self,
        receta: Receta,
        unit_cache: dict[int, UnidadMedidaORM],
        yield_cache: dict[int, float],
    ) -> float:
        if receta.id is not None and receta.id in yield_cache:
            return yield_cache[receta.id]

        if receta.peso_porcion_g is not None and float(receta.peso_porcion_g) > 0:
            rendimiento = float(receta.peso_porcion_g)
        else:
            rendimiento = await self._calcular_rendimiento_por_detalles(receta, unit_cache)
            if rendimiento <= 0:
                rendimiento = float(receta.pax or 1)

        if receta.id is not None:
            yield_cache[receta.id] = rendimiento
        return rendimiento

    async def _calcular_rendimiento_por_detalles(
        self,
        receta: Receta,
        unit_cache: dict[int, UnidadMedidaORM],
    ) -> float:
        total = 0.0
        for detalle in receta.ingredientes:
            unidad = await self._obtener_unidad(detalle.unidad_id, unit_cache)
            familia, factor = self._factor_unidad(unidad)
            if familia in {"peso", "volumen"}:
                total += float(detalle.cantidad) * factor
        return total

    async def _convertir_a_unidad_base(
        self,
        cantidad: float,
        unidad_origen_id: int,
        ingrediente_id: int,
        unit_cache: dict[int, UnidadMedidaORM],
        ingredient_unit_cache: dict[int, int],
    ) -> float:
        unidad_base_id = await self._obtener_unidad_base_ingrediente(ingrediente_id, ingredient_unit_cache)
        if unidad_origen_id == unidad_base_id:
            return float(cantidad)

        unidad_origen = await self._obtener_unidad(unidad_origen_id, unit_cache)
        unidad_base = await self._obtener_unidad(unidad_base_id, unit_cache)
        origen_familia, origen_factor = self._factor_unidad(unidad_origen)
        base_familia, base_factor = self._factor_unidad(unidad_base)

        if origen_familia != base_familia:
            if {origen_familia, base_familia} == {"peso", "volumen"}:
                return self._convertir_peso_volumen_1_a_1(
                    cantidad=float(cantidad),
                    origen_factor=origen_factor,
                    base_factor=base_factor,
                    origen_familia=origen_familia,
                )
            raise ValueError(
                "Unidad incompatible para ingrediente "
                f"{ingrediente_id}: {unidad_origen.abreviatura} no se puede convertir a {unidad_base.abreviatura}"
            )

        return float(cantidad) * origen_factor / base_factor

    def _convertir_peso_volumen_1_a_1(
        self,
        cantidad: float,
        origen_factor: float,
        base_factor: float,
        origen_familia: str,
    ) -> float:
        cantidad_en_base_intermedia = cantidad * origen_factor
        if origen_familia == "peso":
            cantidad_ml = cantidad_en_base_intermedia
            return cantidad_ml / base_factor

        cantidad_g = cantidad_en_base_intermedia
        return cantidad_g / base_factor

    async def _obtener_unidad_base_ingrediente(
        self,
        ingrediente_id: int,
        ingredient_unit_cache: dict[int, int],
    ) -> int:
        if ingrediente_id in ingredient_unit_cache:
            return ingredient_unit_cache[ingrediente_id]

        result = await self.session.execute(
            select(IngredienteORM.unidad_base_id).where(IngredienteORM.id == ingrediente_id)
        )
        unidad_base_id = result.scalar_one_or_none()
        if unidad_base_id is None:
            raise ValueError(f"Ingrediente ID {ingrediente_id} no existe")

        ingredient_unit_cache[ingrediente_id] = int(unidad_base_id)
        return int(unidad_base_id)

    async def _obtener_unidad(
        self,
        unidad_id: int,
        unit_cache: dict[int, UnidadMedidaORM],
    ) -> UnidadMedidaORM:
        if unidad_id in unit_cache:
            return unit_cache[unidad_id]

        result = await self.session.execute(
            select(UnidadMedidaORM).where(UnidadMedidaORM.id == unidad_id)
        )
        unidad = result.scalar_one_or_none()
        if unidad is None:
            raise ValueError(f"Unidad de medida ID {unidad_id} no existe")

        unit_cache[unidad_id] = unidad
        return unidad

    def _factor_unidad(self, unidad: UnidadMedidaORM) -> tuple[str, float]:
        keys = [
            self._normalizar_unidad(unidad.abreviatura),
            self._normalizar_unidad(unidad.nombre),
        ]
        for key in keys:
            if key in _UNIT_FACTORS:
                return _UNIT_FACTORS[key]

        tipo = self._normalizar_unidad(unidad.tipo)
        if tipo == "unidad":
            return ("unidad", 1.0)

        raise ValueError(
            f"No hay conversion configurada para la unidad {unidad.nombre} ({unidad.abreviatura})"
        )

    def _normalizar_unidad(self, value: str | None) -> str:
        if not value:
            return ""
        normalized = unicodedata.normalize("NFD", value.strip().lower())
        normalized = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
        return normalized.replace(".", "").replace(" ", "")

    async def _cargar_receta_en_cache(self, receta_id: int, cache: dict[int, Receta]) -> Receta:
        if receta_id in cache:
            return cache[receta_id]
        receta = await self._cargar_receta_completa(receta_id)
        if receta is None:
            raise ValueError(f"Receta ID {receta_id} no existe")
        cache[receta_id] = receta
        return receta

    async def _cargar_receta_completa(self, receta_id: int) -> Receta | None:
        result = await self.session.execute(select(RecetaORM).where(RecetaORM.id == receta_id))
        receta_orm = result.scalar_one_or_none()
        if receta_orm is None:
            return None

        ingredientes = await self._obtener_detalles(receta_id)
        sub_recetas = await self._obtener_sub_recetas(receta_id)

        return Receta(
            id=receta_orm.id,
            nombre=receta_orm.nombre,
            tipo=TipoRecetaEnum(receta_orm.tipo),
            numero_receta=receta_orm.numero_receta,
            pax=receta_orm.pax,
            peso_porcion_g=float(receta_orm.peso_porcion_g) if receta_orm.peso_porcion_g is not None else None,
            tiempo_prep_min=receta_orm.tiempo_prep_min,
            precio_venta=int(receta_orm.precio_venta) if receta_orm.precio_venta is not None else None,
            categoria_menu=receta_orm.categoria_menu,
            activa=receta_orm.activa,
            ingredientes=ingredientes,
            sub_recetas=sub_recetas,
            imagen=receta_orm.imagen,
            imagen_tipo=receta_orm.imagen_tipo,
        )

    async def _obtener_detalles(self, receta_id: int) -> list[RecetaDetalle]:
        result = await self.session.execute(select(RecetaDetalleORM).where(RecetaDetalleORM.receta_id == receta_id))
        rows = result.scalars().all()
        return [
            RecetaDetalle(
                ingrediente_id=int(row.ingrediente_id),
                cantidad=float(row.cantidad),
                unidad_id=int(row.unidad_id),
                notas=row.notas,
            )
            for row in rows
        ]

    async def _obtener_sub_recetas(self, receta_id: int) -> list[RecetaSub]:
        result = await self.session.execute(select(RecetaSubORM).where(RecetaSubORM.receta_padre_id == receta_id))
        rows = result.scalars().all()
        return [
            RecetaSub(
                receta_padre_id=int(row.receta_padre_id),
                receta_base_id=int(row.receta_base_id),
                cantidad_g=float(row.cantidad_g),
            )
            for row in rows
        ]
