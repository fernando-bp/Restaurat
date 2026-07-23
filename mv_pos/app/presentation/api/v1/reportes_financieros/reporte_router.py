from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query, status, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.presentation.dependencies.auth_deps import get_current_user
from app.presentation.dependencies.db_deps import get_db_session
from app.infrastructure.database.models.finanzas import CompraProveedorORM, GastoOperativoORM

reporte_financiero_router = APIRouter(prefix="/reportes-financieros", tags=["reportes-financieros"])


class GastoPayload(BaseModel):
    fecha: date
    categoria: str = Field(min_length=1, max_length=80)
    monto: float = Field(gt=0)
    descripcion: str | None = None
    es_recurrente: bool = False
    frecuencia: str | None = None
    proxima_fecha: date | None = None


class CompraPayload(BaseModel):
    fecha: date
    proveedor: str = Field(min_length=1, max_length=150)
    ingrediente_id: int | None = None
    descripcion: str = Field(min_length=1, max_length=300)
    cantidad: float = Field(gt=0)
    unidad: str = "unidad"
    costo_total: float = Field(gt=0)


def _money(value: Any) -> float:
    return float(value or 0)


def _date_range(fecha_inicio: date | None, fecha_fin: date | None) -> tuple[datetime, datetime]:
    today = date.today()
    start_date = fecha_inicio or today.replace(day=1)
    end_date = fecha_fin or today
    return (
        datetime.combine(start_date, time.min),
        datetime.combine(end_date, time.max),
    )


def _previous_range(start: datetime, end: datetime) -> tuple[datetime, datetime]:
    days = max((end.date() - start.date()).days + 1, 1)
    previous_end = start - timedelta(microseconds=1)
    previous_start = start - timedelta(days=days)
    return previous_start, previous_end


def _variation(current: float, previous: float) -> float:
    if previous == 0:
        return 100.0 if current > 0 else 0.0
    return round(((current - previous) / previous) * 100, 1)


def _category_label(value: str | None) -> str:
    labels = {
        "desayuno": "Desayunos",
        "entrada": "Entradas",
        "fuerte": "Platos Fuertes",
        "pizza": "Pizzas",
        "pasta": "Pastas",
        "hamburguesa": "Hamburguesas",
        "al_horno": "Al Horno",
        "bebida": "Bebidas",
        "licor": "Licores",
        "postre": "Postres",
        "otro": "Otros",
    }
    return labels.get(value or "otro", "Otros")


def _payment_label(value: str | None) -> str:
    labels = {
        "efectivo": "Efectivo",
        "tarjeta_debito": "Tarjeta Debito",
        "tarjeta_credito": "Tarjeta Credito",
        "nequi": "Nequi",
        "daviplata": "Daviplata",
        "pse": "PSE",
        "cortesia": "Cortesias",
    }
    return labels.get(value or "", value or "Sin pago")


def _build_filters(
    params: dict[str, Any],
    prefix: str = "o",
    payment_prefix: str | None = None,
    recipe_prefix: str | None = None,
    mesa_prefix: str = "m",
) -> tuple[str, dict[str, Any]]:
    clauses: list[str] = []
    values: dict[str, Any] = {}

    if params.get("mesero_id"):
        clauses.append(f"{prefix}.mesero_id = :mesero_id")
        values["mesero_id"] = params["mesero_id"]
    if params.get("estado"):
        clauses.append(f"{prefix}.estado = :estado")
        values["estado"] = params["estado"]
    if params.get("numero_orden"):
        clauses.append(f"{prefix}.id = :numero_orden")
        values["numero_orden"] = params["numero_orden"]
    if params.get("zona"):
        clauses.append(f"{mesa_prefix}.zona = :zona")
        values["zona"] = params["zona"]
    if payment_prefix and params.get("forma_pago"):
        clauses.append(f"{payment_prefix}.forma_pago = :forma_pago")
        values["forma_pago"] = params["forma_pago"]
    if recipe_prefix and params.get("categoria_menu"):
        clauses.append(f"{recipe_prefix}.categoria_menu = :categoria_menu")
        values["categoria_menu"] = params["categoria_menu"]
    if params.get("cajero_id") and payment_prefix:
        clauses.append(f"{payment_prefix}.cajero_id = :cajero_id")
        values["cajero_id"] = params["cajero_id"]

    return (" and " + " and ".join(clauses)) if clauses else "", values


async def _scalar_total(
    db: AsyncSession,
    start: datetime,
    end: datetime,
    params: dict[str, Any],
) -> dict[str, float]:
    extra, values = _build_filters(params, payment_prefix="p")
    result = await db.execute(
        text(
            f"""
            select
              coalesce(sum(base.total_bruto), 0) as ventas_brutas,
              coalesce(sum(base.total_descuento), 0) as descuentos,
              coalesce(sum(base.total_iva), 0) as iva,
              coalesce(sum(base.total_neto), 0) as ventas_netas,
              count(*) as ordenes
            from (
              select o.id, o.total_bruto, o.total_descuento, o.total_iva, o.total_neto
              from ordenes o
              join mesas m on m.id = o.mesa_id
              left join pagos p on p.orden_id = o.id
              where coalesce(o.hora_cierre, p.created_at, o.hora_apertura) between :start and :end
                and (o.estado = 'pagada' or p.id is not null)
                {extra}
              group by o.id, o.total_bruto, o.total_descuento, o.total_iva, o.total_neto
            ) base
            """
        ),
        {"start": start, "end": end, **values},
    )
    row = result.mappings().one()
    return {
        "ventas_brutas": _money(row["ventas_brutas"]),
        "descuentos": _money(row["descuentos"]),
        "iva": _money(row["iva"]),
        "ventas_netas": _money(row["ventas_netas"]),
        "ordenes": int(row["ordenes"] or 0),
    }


async def _recipe_costs(db: AsyncSession) -> dict[int, float]:
    details_result = await db.execute(
        text(
            """
            select rd.receta_id, rd.cantidad, i.precio_unitario,
                   ru.abreviatura as receta_unidad, bu.abreviatura as base_unidad
            from receta_detalle rd
            join ingredientes i on i.id = rd.ingrediente_id
            join unidades_medida ru on ru.id = rd.unidad_id
            join unidades_medida bu on bu.id = i.unidad_base_id
            """
        )
    )
    subs_result = await db.execute(
        text("select receta_padre_id, receta_base_id, cantidad_g from receta_sub")
    )
    recipes_result = await db.execute(
        text("select id, coalesce(peso_porcion_g, pax, 1) as rendimiento from recetas")
    )

    # Recipes store quantities in their selected unit, while an ingredient price is
    # expressed in its base unit.  Pricing 1 kg as if it were 1 g (or vice versa)
    # was the source of the previously impossible Food Cost values.
    unit_factor = {"kg": 1000, "g": 1, "mg": 0.001, "l": 1000, "ml": 1, "und": 1, "unidad": 1, "u": 1}
    def normalized_unit(value: Any) -> str:
        return str(value or "").strip().lower().replace(".", "")

    def quantity_in_base(quantity: float, recipe_unit: Any, base_unit: Any) -> float:
        source, target = normalized_unit(recipe_unit), normalized_unit(base_unit)
        if source == target:
            return quantity
        # Conversion is only safe within a known measurement family. Unknown or
        # incompatible units are retained and exposed as a validation alert.
        weight = {"kg", "g", "mg"}
        volume = {"l", "ml"}
        if (source in weight and target in weight) or (source in volume and target in volume):
            return quantity * unit_factor[source] / unit_factor[target]
        return quantity

    direct_costs: dict[int, float] = defaultdict(float)
    for row in details_result.mappings().all():
        quantity = quantity_in_base(_money(row["cantidad"]), row["receta_unidad"], row["base_unidad"])
        direct_costs[int(row["receta_id"])] += quantity * _money(row["precio_unitario"])

    children: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for row in subs_result.mappings().all():
        children[int(row["receta_padre_id"])].append((int(row["receta_base_id"]), _money(row["cantidad_g"])))

    yields = {
        int(row["id"]): max(_money(row["rendimiento"]), 1)
        for row in recipes_result.mappings().all()
    }
    cache: dict[int, float] = {}

    def cost_for(recipe_id: int, visiting: set[int] | None = None) -> float:
        if recipe_id in cache:
            return cache[recipe_id]
        visiting = visiting or set()
        if recipe_id in visiting:
            return 0.0
        visiting.add(recipe_id)
        total = direct_costs[recipe_id]
        for base_id, cantidad_g in children.get(recipe_id, []):
            total += cost_for(base_id, set(visiting)) * (cantidad_g / yields.get(base_id, 1))
        cache[recipe_id] = total
        return total

    for recipe_id in set(direct_costs) | set(children):
        cost_for(recipe_id)
    return cache


@reporte_financiero_router.get("/")
async def obtener_reporte_financiero(
    fecha_inicio: date | None = Query(None),
    fecha_fin: date | None = Query(None),
    mesero_id: int | None = Query(None),
    cajero_id: int | None = Query(None),
    forma_pago: str | None = Query(None),
    estado: str | None = Query(None),
    zona: str | None = Query(None),
    categoria_menu: str | None = Query(None),
    numero_orden: int | None = Query(None),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    if current_user.get("rol") not in ["cajero", "administrador"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado para reportes financieros.")

    start, end = _date_range(fecha_inicio, fecha_fin)
    previous_start, previous_end = _previous_range(start, end)
    params = {
        "mesero_id": mesero_id,
        "cajero_id": cajero_id,
        "forma_pago": forma_pago,
        "estado": estado,
        "zona": zona,
        "categoria_menu": categoria_menu,
        "numero_orden": numero_orden,
    }

    totals = await _scalar_total(db, start, end, params)
    previous = await _scalar_total(db, previous_start, previous_end, params)
    today_start, today_end = datetime.combine(date.today(), time.min), datetime.combine(date.today(), time.max)
    today_totals = await _scalar_total(db, today_start, today_end, params)

    sales_extra, sales_values = _build_filters(params, payment_prefix="p")
    ventas_result = await db.execute(
        text(
            f"""
            select
              o.id,
              date(coalesce(o.hora_cierre, max(p.created_at), o.hora_apertura)) as fecha,
              time(coalesce(o.hora_cierre, max(p.created_at), o.hora_apertura)) as hora,
              m.numero as mesa,
              coalesce(m.zona, 'Principal') as zona,
              mesero.nombre_completo as mesero,
              group_concat(distinct cajero.nombre_completo order by cajero.nombre_completo separator ', ') as cajero,
              o.total_bruto as subtotal,
              o.total_descuento as descuento,
              o.total_iva as iva,
              o.total_neto as total,
              group_concat(distinct p.forma_pago order by p.forma_pago separator ', ') as pago,
              o.estado
            from ordenes o
            join mesas m on m.id = o.mesa_id
            join usuarios mesero on mesero.id = o.mesero_id
            left join pagos p on p.orden_id = o.id
            left join usuarios cajero on cajero.id = p.cajero_id
            where coalesce(o.hora_cierre, p.created_at, o.hora_apertura) between :start and :end
              and (o.estado = 'pagada' or p.id is not null)
              {sales_extra}
            group by o.id, m.numero, m.zona, mesero.nombre_completo, o.total_bruto, o.total_descuento,
                     o.total_iva, o.total_neto, o.estado, o.hora_cierre, o.hora_apertura
            order by fecha desc, hora desc
            limit 250
            """
        ),
        {"start": start, "end": end, **sales_values},
    )
    ventas = [
        {
            "orden": int(row["id"]),
            "fecha": str(row["fecha"]),
            "hora": str(row["hora"]),
            "mesa": f"Mesa {row['mesa']}",
            "zona": row["zona"],
            "mesero": row["mesero"],
            "cajero": row["cajero"] or "-",
            "subtotal": _money(row["subtotal"]),
            "descuento": _money(row["descuento"]),
            "iva": _money(row["iva"]),
            "total": _money(row["total"]),
            "pago": ", ".join(_payment_label(part) for part in str(row["pago"] or "").split(", ") if part) or "Sin pago",
            "estado": row["estado"],
        }
        for row in ventas_result.mappings().all()
    ]

    items_extra, item_values = _build_filters(params, payment_prefix="p", recipe_prefix="r")
    items_result = await db.execute(
        text(
            f"""
            with ordenes_filtradas as (
              select o.id
              from ordenes o
              join mesas m on m.id = o.mesa_id
              join orden_items oi_filter on oi_filter.orden_id = o.id
              join recetas r on r.id = oi_filter.receta_id
              left join pagos p on p.orden_id = o.id
              where coalesce(o.hora_cierre, p.created_at, o.hora_apertura) between :start and :end
                and (o.estado = 'pagada' or p.id is not null)
                {items_extra}
              group by o.id
            )
            select
              r.id as receta_id,
              r.nombre as plato,
              r.categoria_menu,
              sum(oi.cantidad) as vendidos,
              sum(oi.cantidad * oi.precio_unitario) as ingresos
            from orden_items oi
            join ordenes_filtradas ofi on ofi.id = oi.orden_id
            join recetas r on r.id = oi.receta_id
            where oi.estado <> 'cancelado'
            group by r.id, r.nombre, r.categoria_menu
            order by ingresos desc
            """
        ),
        {"start": start, "end": end, **item_values},
    )
    recipe_costs = await _recipe_costs(db)
    rankings = []
    categories: dict[str, dict[str, float]] = defaultdict(lambda: {"ventas": 0.0, "unidades": 0.0, "costo": 0.0})
    for row in items_result.mappings().all():
        receta_id = int(row["receta_id"])
        ingresos = _money(row["ingresos"])
        vendidos = _money(row["vendidos"])
        costo = recipe_costs.get(receta_id, 0.0) * vendidos
        utilidad = ingresos - costo
        food_cost = (costo / ingresos * 100) if ingresos else 0
        margin = 100 - food_cost if ingresos else 0
        category = _category_label(row["categoria_menu"])
        categories[category]["ventas"] += ingresos
        categories[category]["unidades"] += vendidos
        categories[category]["costo"] += costo
        rankings.append(
            {
                "receta_id": receta_id,
                "plato": row["plato"],
                "categoria": category,
                "vendidos": int(vendidos),
                "ingresos": ingresos,
                "costo": costo,
                "food_cost_pct": round(food_cost, 1),
                "margen_pct": round(margin, 1),
                "utilidad": utilidad,
            }
        )

    day_extra, day_values = _build_filters(params, payment_prefix="p")
    daily_result = await db.execute(
        text(
            f"""
            select base.dia,
                   coalesce(sum(base.total_neto), 0) as ventas,
                   count(*) as ordenes
            from (
              select o.id,
                     date(coalesce(o.hora_cierre, max(p.created_at), o.hora_apertura)) as dia,
                     o.total_neto
              from ordenes o
              join mesas m on m.id = o.mesa_id
              left join pagos p on p.orden_id = o.id
              where coalesce(o.hora_cierre, p.created_at, o.hora_apertura) between :start and :end
                and (o.estado = 'pagada' or p.id is not null)
                {day_extra}
              group by o.id, o.hora_cierre, o.hora_apertura, o.total_neto
            ) base
            group by base.dia
            order by dia
            """
        ),
        {"start": start, "end": end, **day_values},
    )
    ventas_por_dia = [
        {"fecha": str(row["dia"]), "ventas": _money(row["ventas"]), "ordenes": int(row["ordenes"] or 0)}
        for row in daily_result.mappings().all()
    ]

    payment_extra, payment_values = _build_filters(params, prefix="o", payment_prefix="p")
    payments_result = await db.execute(
        text(
            f"""
            select p.forma_pago, count(*) as cantidad, coalesce(sum(p.monto), 0) as total
            from pagos p
            join ordenes o on o.id = p.orden_id
            join mesas m on m.id = o.mesa_id
            where p.created_at between :start and :end
              {payment_extra}
            group by p.forma_pago
            order by total desc
            """
        ),
        {"start": start, "end": end, **payment_values},
    )
    metodos_pago = []
    total_pagos = 0.0
    for row in payments_result.mappings().all():
        total = _money(row["total"])
        total_pagos += total
        metodos_pago.append({"metodo": _payment_label(row["forma_pago"]), "cantidad": int(row["cantidad"] or 0), "total": total})
    for item in metodos_pago:
        item["porcentaje"] = round((item["total"] / total_pagos * 100) if total_pagos else 0, 1)

    meseros_result = await db.execute(
        text(
            f"""
            select base.nombre, count(*) as ordenes, coalesce(sum(base.total_neto), 0) as ventas
            from (
              select o.id, u.nombre_completo as nombre, o.total_neto
              from ordenes o
              join usuarios u on u.id = o.mesero_id
              join mesas m on m.id = o.mesa_id
              left join pagos p on p.orden_id = o.id
              where coalesce(o.hora_cierre, p.created_at, o.hora_apertura) between :start and :end
                and (o.estado = 'pagada' or p.id is not null)
                {day_extra}
              group by o.id, u.nombre_completo, o.total_neto
            ) base
            group by base.nombre
            order by ventas desc
            limit 10
            """
        ),
        {"start": start, "end": end, **day_values},
    )
    ranking_meseros = [
        {
            "nombre": row["nombre"],
            "ordenes": int(row["ordenes"] or 0),
            "ventas": _money(row["ventas"]),
            "ticket": _money(row["ventas"]) / max(int(row["ordenes"] or 0), 1),
            "comision": _money(row["ventas"]) * 0.02,
        }
        for row in meseros_result.mappings().all()
    ]

    cajeros_result = await db.execute(
        text(
            """
            select u.nombre_completo as nombre, count(p.id) as pagos, coalesce(sum(p.monto), 0) as total
            from pagos p
            join usuarios u on u.id = p.cajero_id
            join ordenes o on o.id = p.orden_id
            join mesas m on m.id = o.mesa_id
            where p.created_at between :start and :end
            group by u.id, u.nombre_completo
            order by total desc
            limit 10
            """
        ),
        {"start": start, "end": end},
    )
    ranking_cajeros = [
        {"nombre": row["nombre"], "pagos": int(row["pagos"] or 0), "total": _money(row["total"]), "diferencia": 0}
        for row in cajeros_result.mappings().all()
    ]

    category_rows = []
    max_category = max((value["ventas"] for value in categories.values()), default=1)
    for name, value in sorted(categories.items(), key=lambda item: item[1]["ventas"], reverse=True):
        category_rows.append(
            {
                "categoria": name,
                "ventas": value["ventas"],
                "unidades": int(value["unidades"]),
                "costo": value["costo"],
                "porcentaje": round((value["ventas"] / max_category) * 100, 1) if max_category else 0,
                "food_cost_pct": round((value["costo"] / value["ventas"] * 100) if value["ventas"] else 0, 1),
            }
        )

    total_costo = sum(item["costo"] for item in rankings)
    ventas_netas = totals["ventas_netas"]
    food_cost = (total_costo / ventas_netas * 100) if ventas_netas else 0.0
    margen_bruto = 100 - food_cost if ventas_netas else 0.0
    gastos_result = await db.execute(
        text("select coalesce(sum(monto), 0) as total from gastos_operativos where fecha between :start and :end"),
        {"start": start.date(), "end": end.date()},
    )
    gastos_operativos = _money(gastos_result.mappings().one()["total"])
    cierres_result = await db.execute(
        text("""
            select coalesce(sum(total_ventas), 0) as ventas_cierre,
                   coalesce(sum(total_efectivo_contado + total_tarjeta + total_transferencia + total_cortesia), 0) as contado
            from cierre_caja where fecha between :start and :end
        """),
        {"start": start.date(), "end": end.date()},
    )
    cierres = cierres_result.mappings().one()
    ventas_cierre, contado = _money(cierres["ventas_cierre"]), _money(cierres["contado"])
    alertas_costeo = [item for item in rankings if item["food_cost_pct"] > 100]

    return {
        "periodo": {"inicio": str(start.date()), "fin": str(end.date())},
        "metricas": {
            "ventas_dia": today_totals["ventas_netas"],
            "ventas_periodo": ventas_netas,
            "ticket_promedio": ventas_netas / max(totals["ordenes"], 1),
            "numero_ordenes": totals["ordenes"],
            "variacion_ventas": _variation(totals["ventas_netas"], previous["ventas_netas"]),
            "variacion_ordenes": _variation(totals["ordenes"], previous["ordenes"]),
        },
        "resumen": {
            "ventas_brutas": totals["ventas_brutas"],
            "total_descuentos": totals["descuentos"],
            "iva_recaudado": totals["iva"],
            "ventas_netas": ventas_netas,
            "propinas": 0,
            "clientes": 0,
            "promedio_cliente": 0,
            "promedio_mesa": ventas_netas / max(totals["ordenes"], 1),
        },
        "ventas": ventas,
        "ventas_por_dia": ventas_por_dia,
        "metodos_pago": metodos_pago,
        "rankings": {
            "platos": rankings[:15],
            "meseros": ranking_meseros,
            "cajeros": ranking_cajeros,
        },
        "categorias": category_rows,
        "rentabilidad": {
            "food_cost_promedio": round(food_cost, 1),
            "margen_bruto": round(margen_bruto, 1),
            "utilidad_estimada": ventas_netas - total_costo,
            "costo_ingredientes": total_costo,
            "costo_total": total_costo,
            "ventas_netas": ventas_netas,
            "rentabilidad_pct": round(margen_bruto, 1),
            "por_categoria": category_rows,
        },
        "estado_resultados": {
            "ventas_brutas": totals["ventas_brutas"],
            "descuentos": totals["descuentos"],
            "ventas_netas": ventas_netas,
            "costo_ventas": total_costo,
            "utilidad_bruta": ventas_netas - total_costo,
            "margen_bruto": round(margen_bruto, 1),
            "gastos_operativos": gastos_operativos,
            "utilidad_neta": ventas_netas - total_costo - gastos_operativos,
            "margen_neto": round(((ventas_netas - total_costo - gastos_operativos) / ventas_netas * 100) if ventas_netas else 0, 1),
        },
        "conciliacion_caja": {
            "ventas_sistema": ventas_netas,
            "ventas_cierres": ventas_cierre,
            "total_contado": contado,
            "diferencia": contado - ventas_netas,
        },
        "alertas_costeo": alertas_costeo,
        "comparativo": {
            "actual": totals,
            "anterior": previous,
            "variacion_ventas": _variation(totals["ventas_netas"], previous["ventas_netas"]),
            "variacion_ordenes": _variation(totals["ordenes"], previous["ordenes"]),
            "variacion_ticket": _variation(
                ventas_netas / max(totals["ordenes"], 1),
                previous["ventas_netas"] / max(previous["ordenes"], 1),
            ),
        },
    }


@reporte_financiero_router.get("/gastos")
async def listar_gastos(
    fecha_inicio: date | None = None, fecha_fin: date | None = None,
    current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db_session),
):
    if current_user.get("rol") not in ["cajero", "administrador"]:
        raise HTTPException(status_code=403, detail="No autorizado.")
    statement = select(GastoOperativoORM).order_by(GastoOperativoORM.fecha.desc(), GastoOperativoORM.id.desc())
    if fecha_inicio: statement = statement.where(GastoOperativoORM.fecha >= fecha_inicio)
    if fecha_fin: statement = statement.where(GastoOperativoORM.fecha <= fecha_fin)
    rows = (await db.execute(statement)).scalars().all()
    return [{"id": row.id, "fecha": str(row.fecha), "categoria": row.categoria, "monto": _money(row.monto), "descripcion": row.descripcion, "es_recurrente": row.es_recurrente, "frecuencia": row.frecuencia} for row in rows]


@reporte_financiero_router.post("/gastos", status_code=status.HTTP_201_CREATED)
async def crear_gasto(payload: GastoPayload, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    if current_user.get("rol") != "administrador": raise HTTPException(status_code=403, detail="Solo administradores pueden registrar gastos.")
    row = GastoOperativoORM(**payload.model_dump())
    db.add(row); await db.commit(); await db.refresh(row)
    return {"id": row.id}


@reporte_financiero_router.get("/compras")
async def listar_compras(current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    if current_user.get("rol") not in ["cajero", "administrador"]: raise HTTPException(status_code=403, detail="No autorizado.")
    rows = (await db.execute(select(CompraProveedorORM).order_by(CompraProveedorORM.fecha.desc(), CompraProveedorORM.id.desc()))).scalars().all()
    return [{"id": r.id, "fecha": str(r.fecha), "proveedor": r.proveedor, "descripcion": r.descripcion, "cantidad": _money(r.cantidad), "unidad": r.unidad, "costo_total": _money(r.costo_total), "costo_unitario": _money(r.costo_total) / max(_money(r.cantidad), 1)} for r in rows]


@reporte_financiero_router.post("/compras", status_code=status.HTTP_201_CREATED)
async def crear_compra(payload: CompraPayload, current_user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db_session)):
    if current_user.get("rol") != "administrador": raise HTTPException(status_code=403, detail="Solo administradores pueden registrar compras.")
    row = CompraProveedorORM(**payload.model_dump())
    db.add(row); await db.commit(); await db.refresh(row)
    return {"id": row.id}
