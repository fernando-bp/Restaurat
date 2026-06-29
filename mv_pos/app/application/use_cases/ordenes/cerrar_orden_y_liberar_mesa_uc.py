from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.infrastructure.database.models.mesa import OrdenORM, MesaORM
from app.domain.enums.estado_orden import EstadoOrdenEnum
from app.domain.enums.estado_mesa import EstadoMesaEnum


class CerrarOrdenYLiberarMesaUC:
    """Use case para cerrar orden y liberar mesa después de pagar"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def ejecutar(self, orden_id: int) -> dict:
        """
        Cierra una orden y libera la mesa asociada.
        
        Args:
            orden_id: ID de la orden a cerrar
            
        Returns:
            dict con información de la operación
        """
        # Obtener la orden
        resultado_orden = await self.db.execute(
            select(OrdenORM).where(OrdenORM.id == orden_id)
        )
        orden = resultado_orden.scalar_one_or_none()
        
        if not orden:
            raise ValueError(f"Orden {orden_id} no encontrada")
        
        if orden.estado == EstadoOrdenEnum.PAGADA.value:
            raise ValueError("Esta orden ya fue pagada")
        
        # Obtener la mesa
        resultado_mesa = await self.db.execute(
            select(MesaORM).where(MesaORM.id == orden.mesa_id)
        )
        mesa = resultado_mesa.scalar_one_or_none()
        
        if not mesa:
            raise ValueError(f"Mesa {orden.mesa_id} no encontrada")
        
        # Actualizar estado de la orden
        orden.estado = EstadoOrdenEnum.PAGADA.value
        orden.hora_cierre = datetime.utcnow()
        
        # Liberar la mesa
        mesa.estado = EstadoMesaEnum.LIBRE.value
        mesa.comensales_actuales = 0
        
        await self.db.flush()
        
        return {
            "orden_id": orden.id,
            "mesa_id": mesa.id,
            "estado_orden": "pagada",
            "estado_mesa": mesa.estado,
            "cerrada_at": orden.hora_cierre
        }
