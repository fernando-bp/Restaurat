from decimal import Decimal
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.database.models.pago_dividido import PagoDivididoORM, PersonaPagoDivididoORM
from app.infrastructure.database.models.pago import PagoORM
from app.application.dtos.pago_dividido_dto import RegistrarPagoPersonaResponse


class RegistrarPagoPersonaDividoUC:
    """Use case para registrar el pago de una persona en un pago dividido"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def ejecutar(
        self,
        pago_dividido_id: int,
        numero_persona: int,
        forma_pago: str,
        cajero_id: int,
        monto_recibido: Decimal = None,
        referencia_datafono: str = None,
        numero_comprobante: str = None
    ) -> RegistrarPagoPersonaResponse:
        """
        Registra el pago de una persona en un pago dividido.
        
        Args:
            pago_dividido_id: ID del pago dividido
            numero_persona: Número de la persona (1, 2, 3, ...)
            forma_pago: Forma de pago (efectivo, tarjeta_debito, etc)
            cajero_id: ID del cajero que registra el pago
            monto_recibido: Monto recibido (solo para efectivo)
            referencia_datafono: Referencia del datafono (para tarjeta)
            numero_comprobante: Número de comprobante (para transferencia)
            
        Returns:
            RegistrarPagoPersonaResponse con detalles del pago registrado
        """
        # Obtener pago dividido
        resultado_pago = await self.db.execute(
            select(PagoDivididoORM).where(PagoDivididoORM.id == pago_dividido_id)
        )
        pago_dividido = resultado_pago.scalar_one_or_none()
        
        if not pago_dividido:
            raise ValueError(f"Pago dividido {pago_dividido_id} no encontrado")
        
        if pago_dividido.completado:
            raise ValueError("Este pago dividido ya ha sido completado")
        
        # Obtener la persona
        resultado_persona = await self.db.execute(
            select(PersonaPagoDivididoORM).where(
                PersonaPagoDivididoORM.pago_dividido_id == pago_dividido_id,
                PersonaPagoDivididoORM.numero_persona == numero_persona
            )
        )
        persona = resultado_persona.scalar_one_or_none()
        
        if not persona:
            raise ValueError(f"Persona {numero_persona} no encontrada en este pago dividido")
        
        if persona.pagado:
            raise ValueError(f"La persona {numero_persona} ya ha pagado")
        
        # Validar forma de pago
        self._validar_forma_pago(forma_pago, monto_recibido, referencia_datafono, numero_comprobante)
        
        # Calcular cambio si es efectivo
        cambio = Decimal(0)
        if forma_pago == "efectivo":
            if monto_recibido is None or monto_recibido < persona.monto:
                raise ValueError("Monto recibido insuficiente para efectivo")
            cambio = monto_recibido - persona.monto
        
        # Actualizar la persona
        persona.pagado = True
        persona.forma_pago = forma_pago
        persona.monto_recibido = monto_recibido
        persona.cambio_entregado = cambio if forma_pago == "efectivo" else None
        persona.referencia_datafono = referencia_datafono
        persona.numero_comprobante = numero_comprobante
        persona.cajero_id = cajero_id
        persona.pagado_at = datetime.utcnow()
        
        # Registrar en tabla de pagos
        pago_orm = PagoORM(
            orden_id=pago_dividido.orden_id,
            forma_pago=forma_pago,
            monto=persona.monto,
            monto_recibido=monto_recibido,
            cambio_entregado=cambio if forma_pago == "efectivo" else None,
            referencia_datafono=referencia_datafono,
            numero_comprobante=numero_comprobante,
            cajero_id=cajero_id
        )
        self.db.add(pago_orm)
        
        await self.db.flush()
        
        # Verificar si todos pagaron
        resultado_todas = await self.db.execute(
            select(PersonaPagoDivididoORM).where(
                PersonaPagoDivididoORM.pago_dividido_id == pago_dividido_id
            )
        )
        todas_personas = resultado_todas.scalars().all()
        todas_pagaron = all(p.pagado for p in todas_personas)
        
        if todas_pagaron:
            pago_dividido.completado = True
            pago_dividido.completed_at = datetime.utcnow()
        
        await self.db.flush()
        
        return RegistrarPagoPersonaResponse(
            numero_persona=numero_persona,
            monto=persona.monto,
            forma_pago=forma_pago,
            cambio_entregado=cambio if forma_pago == "efectivo" else None,
            pagado_at=persona.pagado_at,
            completado_division=todas_pagaron
        )
    
    def _validar_forma_pago(
        self,
        forma_pago: str,
        monto_recibido: Decimal = None,
        referencia_datafono: str = None,
        numero_comprobante: str = None
    ):
        """Valida que los datos de forma de pago sean correctos"""
        if forma_pago == "efectivo" and monto_recibido is None:
            raise ValueError("monto_recibido es requerido para pago en efectivo")
        
        if forma_pago in ("tarjeta_debito", "tarjeta_credito") and not referencia_datafono:
            raise ValueError(f"referencia_datafono es obligatoria para {forma_pago}")
        
        if forma_pago in ("nequi", "daviplata", "pse") and not numero_comprobante:
            raise ValueError(f"numero_comprobante es obligatorio para {forma_pago}")
