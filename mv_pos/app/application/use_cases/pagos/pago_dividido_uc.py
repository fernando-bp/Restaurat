from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.infrastructure.database.models.pago_dividido import PagoDivididoORM, PersonaPagoDivididoORM
from app.application.dtos.pago_dividido_dto import PagoDivididoResumenDTO, PersonaPagoDivididoDTO


class CrearPagoDivididoUC:
    """Use case para crear una división de pago"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def ejecutar(
        self,
        orden_id: int,
        numero_personas: int,
        monto_total: Decimal,
        montos_personas: list[Decimal] | None = None
    ) -> PagoDivididoResumenDTO:
        """
        Crea una división de pago para una orden.
        
        Args:
            orden_id: ID de la orden a dividir
            numero_personas: Número de personas en la división
            monto_total: Monto total a dividir
            
        Returns:
            PagoDivididoResumenDTO con la división creada
        """
        if numero_personas < 2:
            raise ValueError("La división debe ser entre al menos 2 personas")
        
        if monto_total <= 0:
            raise ValueError("El monto total debe ser mayor a 0")
        
        # Calcular montos por persona. Si no vienen montos custom, se divide en partes iguales.
        if montos_personas:
            if len(montos_personas) != numero_personas:
                raise ValueError("Debe enviar un monto por cada persona")

            if any(monto <= 0 for monto in montos_personas):
                raise ValueError("Cada persona debe tener un monto mayor a 0")

            suma_montos = sum(montos_personas, Decimal(0))
            if abs(suma_montos - monto_total) > Decimal("0.01"):
                raise ValueError("La suma de los montos por persona debe coincidir con el total")

            montos_calculados = montos_personas
        else:
            monto_por_persona = monto_total / Decimal(numero_personas)
            montos_calculados = [monto_por_persona for _ in range(numero_personas)]

        monto_por_persona = monto_total / Decimal(numero_personas)
        
        # Crear el registro de pago dividido
        pago_dividido = PagoDivididoORM(
            orden_id=orden_id,
            numero_personas=numero_personas,
            monto_total=monto_total
        )
        self.db.add(pago_dividido)
        await self.db.flush()  # Para obtener el ID generado
        
        # Crear personas con sus montos
        personas = []
        for i, monto_persona in enumerate(montos_calculados, start=1):
            persona = PersonaPagoDivididoORM(
                pago_dividido_id=pago_dividido.id,
                numero_persona=i,
                monto=monto_persona
            )
            self.db.add(persona)
            personas.append(
                PersonaPagoDivididoDTO(
                    numero_persona=i,
                    monto=monto_persona,
                    pagado=False
                )
            )
        
        await self.db.flush()
        
        return PagoDivididoResumenDTO(
            id=pago_dividido.id,
            orden_id=orden_id,
            numero_personas=numero_personas,
            monto_total=monto_total,
            monto_por_persona=monto_por_persona,
            personas_pagadas=0,
            completado=False,
            created_at=pago_dividido.created_at,
            personas=personas
        )


class ObtenerResumenPagoDivididoUC:
    """Use case para obtener el resumen de un pago dividido"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def ejecutar(self, pago_dividido_id: int) -> PagoDivididoResumenDTO:
        """Obtiene el resumen de un pago dividido"""
        from sqlalchemy import select
        
        # Obtener pago dividido
        resultado = await self.db.execute(
            select(PagoDivididoORM).where(PagoDivididoORM.id == pago_dividido_id)
        )
        pago_dividido = resultado.scalar_one_or_none()
        
        if not pago_dividido:
            raise ValueError(f"Pago dividido {pago_dividido_id} no encontrado")
        
        # Obtener personas
        resultado_personas = await self.db.execute(
            select(PersonaPagoDivididoORM).where(
                PersonaPagoDivididoORM.pago_dividido_id == pago_dividido_id
            ).order_by(PersonaPagoDivididoORM.numero_persona)
        )
        personas_orm = resultado_personas.scalars().all()
        
        personas = [
            PersonaPagoDivididoDTO(
                numero_persona=p.numero_persona,
                monto=p.monto,
                pagado=p.pagado,
                forma_pago=p.forma_pago,
                monto_recibido=p.monto_recibido,
                cambio_entregado=p.cambio_entregado,
                pagado_at=p.pagado_at
            )
            for p in personas_orm
        ]
        
        personas_pagadas = sum(1 for p in personas if p.pagado)
        
        return PagoDivididoResumenDTO(
            id=pago_dividido.id,
            orden_id=pago_dividido.orden_id,
            numero_personas=pago_dividido.numero_personas,
            monto_total=pago_dividido.monto_total,
            monto_por_persona=pago_dividido.monto_total / Decimal(pago_dividido.numero_personas),
            personas_pagadas=personas_pagadas,
            completado=pago_dividido.completado,
            created_at=pago_dividido.created_at,
            personas=personas
        )
