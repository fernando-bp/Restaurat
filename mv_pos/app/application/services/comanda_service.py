from __future__ import annotations
from datetime import datetime
from app.application.dtos.comanda_dto import ComandaDTO


class ComandaService:
    """Servicio para generar y formatear comandas para impresión."""

    @staticmethod
    def generar_ticket(comanda: ComandaDTO) -> str:
        """
        Genera un ticket de comanda formateado para impresora de papel.
        
        Args:
            comanda: DTO con información de la comanda
            
        Returns:
            String formateado para imprimir
        """
        linea = "=" * 40
        
        ticket = f"""
{linea}
              MV-POS COMANDA
{linea}
Hora: {comanda.hora.strftime('%H:%M:%S')}
Mesa: {comanda.mesa_numero}
Comensales: {comanda.num_comensales}
Orden ID: {comanda.orden_id}
{linea}

ITEMS:
"""
        
        for i, item in enumerate(comanda.items, 1):
            ticket += f"{i}. {item.receta_nombre}\n"
            ticket += f"   Cantidad: {item.cantidad}\n"
            if item.observaciones:
                ticket += f"   Notas: {item.observaciones}\n"
            ticket += "\n"

        if comanda.notas_generales:
            ticket += f"\nNOTAS GENERALES:\n{comanda.notas_generales}\n"

        ticket += f"\n{linea}\n"
        
        return ticket
