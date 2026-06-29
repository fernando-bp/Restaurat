from app.domain.entities.orden import Orden
from app.domain.entities.orden_item import OrdenItem
from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.infrastructure.database.models.mesa import OrdenORM


def orden_from_orm(orm: OrdenORM) -> Orden:
    """Convierte OrdenORM a entidad Orden"""
    if not orm:
        return None

    items = []
    if hasattr(orm, 'items') and orm.items:
        items = [
            OrdenItem(
                id=item.id,
                orden_id=item.orden_id,
                receta_id=item.receta_id,
                cantidad=item.cantidad,
                precio_unitario=int(item.precio_unitario),
                estado=item.estado,
                observaciones=item.notas,
            )
            for item in orm.items
        ]

    return Orden(
        id=orm.id,
        mesa_id=orm.mesa_id,
        mesero_id=orm.mesero_id,
        num_comensales=orm.num_comensales,
        estado=EstadoOrdenEnum(orm.estado),
        hora_apertura=orm.hora_apertura,
        notas_generales=orm.notas_generales,
        hora_confirmacion=orm.hora_confirmacion,
        hora_cierre=orm.hora_cierre,
        total_bruto=int(orm.total_bruto or 0),
        total_descuento=int(orm.total_descuento or 0),
        total_iva=int(orm.total_iva or 0),
        total_neto=int(orm.total_neto or 0),
        items=items,
    )


def orm_from_orden(orden: Orden) -> dict:
    """Convierte entidad Orden a diccionario para OrdenORM"""
    return {
        'id': orden.id,
        'mesa_id': orden.mesa_id,
        'mesero_id': orden.mesero_id,
        'num_comensales': orden.num_comensales,
        'estado': orden.estado.value,
        'hora_apertura': orden.hora_apertura,
        'notas_generales': orden.notas_generales,
        'hora_confirmacion': orden.hora_confirmacion,
        'hora_cierre': orden.hora_cierre,
        'total_bruto': orden.total_bruto,
        'total_descuento': orden.total_descuento,
        'total_iva': orden.total_iva,
        'total_neto': orden.total_neto,
    }
