"""
RF-27: Generar cuenta detallada con ítems, cantidades, descuentos e IVA
"""
from decimal import Decimal
from datetime import datetime
from typing import List, Dict, Any

from app.infrastructure.database.models.orden_item import OrdenItemORM
from app.infrastructure.database.models.orden import OrdenORM


class GenerarCuentaUseCase:
    """Genera la cuenta detallada de una mesa (RF-27)"""
    
    def __init__(self, db_session):
        self.db = db_session

    def ejecutar(self, orden_id: int) -> Dict[str, Any]:
        """
        Genera cuenta detallada para impresión y exportación a PDF
        
        Retorna:
        {
            'orden_id': int,
            'mesa_numero': str,
            'num_comensales': int,
            'items': [
                {'receta': str, 'cantidad': int, 'precio_unitario': int, 'subtotal': int}
            ],
            'total_bruto': int,
            'descuentos': [
                {'motivo': str, 'porcentaje': float, 'monto': int}
            ],
            'total_descuento': int,
            'iva': int,
            'total_neto': int,
            'fecha_apertura': datetime
        }
        """
        orden = self.db.query(OrdenORM).filter_by(id=orden_id).first()
        
        if not orden:
            raise ValueError(f"Orden {orden_id} no encontrada")

        # Construir items detallados
        items = []
        for item in orden.items:
            if item.estado != 'cancelado':
                items.append({
                    'id': item.id,
                    'receta': item.receta.nombre if item.receta else 'N/A',
                    'cantidad': item.cantidad,
                    'precio_unitario': item.precio_unitario,
                    'subtotal': item.cantidad * item.precio_unitario,
                    'modificadores': item.modificadores,
                    'notas': item.notas
                })

        # Descuentos
        descuentos = []
        total_descuento = Decimal(0)
        
        if orden.descuentos:
            for desc in orden.descuentos:
                descuentos.append({
                    'motivo': desc.motivo,
                    'porcentaje': desc.porcentaje,
                    'monto': desc.monto
                })
                total_descuento += desc.monto

        total_bruto = sum(item['subtotal'] for item in items)
        
        # Impuesto definido para esta operación: 8%.
        base_iva = total_bruto - total_descuento
        iva = base_iva * Decimal('0.08')
        total_neto = base_iva + iva

        return {
            'orden_id': orden.id,
            'mesa_numero': orden.mesa.numero if orden.mesa else 'N/A',
            'num_comensales': orden.num_comensales,
            'items': items,
            'total_bruto': total_bruto,
            'descuentos': descuentos,
            'total_descuento': total_descuento,
            'iva': iva,
            'total_neto': total_neto,
            'fecha_apertura': orden.hora_apertura,
            'mesero': orden.mesero.nombre_completo if orden.mesero else 'N/A'
        }
