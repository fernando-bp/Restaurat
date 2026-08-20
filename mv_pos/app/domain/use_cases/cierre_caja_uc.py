from __future__ import annotations
from datetime import datetime, date, time
from typing import Tuple, Optional, Dict, List
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.usuario_repository import UsuarioRepository
from app.domain.exceptions.auth_exceptions import InvalidCredentialsException
from app.infrastructure.database.models.pago import PagoORM, CierreCajaORM, DescuentoORM
from app.infrastructure.database.models.orden_item import OrdenItemORM
from app.infrastructure.database.models.mesa import MesaORM, OrdenORM


class CierreCajaUseCase:
    """Use case para realizar el cierre de caja diario."""

    def __init__(self, db_session: AsyncSession, usuario_repo: UsuarioRepository, restaurante_id: int = 1):
        self.db = db_session
        self.usuario_repo = usuario_repo
        self.restaurante_id = restaurante_id

    async def _obtener_inicio_periodo_caja(self, hasta: datetime) -> Optional[datetime]:
        result = await self.db.execute(
            select(func.coalesce(CierreCajaORM.firmado_at, CierreCajaORM.created_at))
            .where(
                CierreCajaORM.restaurante_id == self.restaurante_id,
                func.coalesce(CierreCajaORM.firmado_at, CierreCajaORM.created_at) < hasta,
            )
            .order_by(func.coalesce(CierreCajaORM.firmado_at, CierreCajaORM.created_at).desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def verificar_mesas_cerradas(self) -> Tuple[bool, Optional[List[int]]]:
        """Verifica que todas las mesas estén cerradas.

        Returns:
            (Tuple): (todas_cerradas, lista_mesas_abiertas)
                - todas_cerradas: bool indicando si todas las mesas están cerradas
                - lista_mesas_abiertas: list con IDs de mesas aún abiertas o None
        """
        # Obtener todas las órdenes abiertas del día
        result = await self.db.execute(
            select(OrdenORM.mesa_id)
            .where(
                and_(
                    OrdenORM.restaurante_id == self.restaurante_id,
                    OrdenORM.estado.in_(['abierta', 'en_preparacion', 'lista', 'en_espera_cuenta']),
                    func.date(OrdenORM.hora_apertura) == date.today()
                )
            )
            .distinct()
        )
        mesas_abiertas = result.scalars().all()
        
        if mesas_abiertas:
            return False, list(mesas_abiertas)
        return True, None
    
    async def obtener_resumen_caja(self, fecha: date, reiniciar_si_cerrado: bool = False) -> Dict:
        """Obtiene el resumen de caja antes del conteo de efectivo.
        
        Args:
            fecha: Fecha del cierre (YYYY-MM-DD)
            
        Returns:
            Dict con resúmenes por forma de pago y totales
        """
        if reiniciar_si_cerrado:
            cierre_existente = await self.db.execute(
                select(CierreCajaORM.id).where(CierreCajaORM.fecha == fecha)
            )
            if cierre_existente.scalar_one_or_none() is not None:
                return self._resumen_en_ceros(fecha)

        # Obtener todos los pagos del día
        fin_periodo = datetime.utcnow() if fecha == date.today() else datetime.combine(fecha, time.max)
        inicio_periodo = await self._obtener_inicio_periodo_caja(fin_periodo)

        filtros_pagos = [
            PagoORM.created_at <= fin_periodo,
            PagoORM.forma_pago != 'cortesia',
            OrdenORM.restaurante_id == self.restaurante_id,
        ]
        filtros_descuentos = [
            DescuentoORM.created_at <= fin_periodo,
            OrdenORM.restaurante_id == self.restaurante_id,
        ]

        if inicio_periodo is not None:
            filtros_pagos.append(PagoORM.created_at > inicio_periodo)
            filtros_descuentos.append(DescuentoORM.created_at > inicio_periodo)
        else:
            inicio_dia = datetime.combine(fecha, time.min)
            filtros_pagos.append(PagoORM.created_at >= inicio_dia)
            filtros_descuentos.append(DescuentoORM.created_at >= inicio_dia)

        result = await self.db.execute(
            select(PagoORM)
            .join(OrdenORM, PagoORM.orden_id == OrdenORM.id)
            .where(and_(*filtros_pagos))
        )
        pagos = result.scalars().all()

        # Agrupar por forma de pago
        resumen = {
            'efectivo': {'total': 0, 'cantidad': 0},
            'tarjeta_debito': {'total': 0, 'cantidad': 0},
            'tarjeta_credito': {'total': 0, 'cantidad': 0},
            'nequi': {'total': 0, 'cantidad': 0},
            'daviplata': {'total': 0, 'cantidad': 0},
            'pse': {'total': 0, 'cantidad': 0},
            'qr_breb': {'total': 0, 'cantidad': 0},
        }

        for pago in pagos:
            if pago.forma_pago in resumen:
                resumen[pago.forma_pago]['total'] += float(pago.monto)
                resumen[pago.forma_pago]['cantidad'] += 1

        # Obtener descuentos del día
        result = await self.db.execute(
            select(func.coalesce(func.sum(DescuentoORM.monto), 0))
            .join(OrdenORM, DescuentoORM.orden_id == OrdenORM.id)
            .where(and_(*filtros_descuentos))
        )
        total_descuentos = float(result.scalar())
        
        # Calcular totales
        total_ventas = sum(pago['total'] for pago in resumen.values())
        total_efectivo = resumen['efectivo']['total']
        total_tarjeta_debito = resumen['tarjeta_debito']['total']
        total_tarjeta_credito = resumen['tarjeta_credito']['total']
        total_transferencia = (
            resumen['nequi']['total'] +
            resumen['daviplata']['total'] +
            resumen['pse']['total'] +
            resumen['qr_breb']['total']
        )
        
        return {
            'fecha': str(fecha),
            'total_ventas': total_ventas,
            'total_efectivo_sistema': total_efectivo,
            'total_tarjeta_debito': total_tarjeta_debito,
            'total_tarjeta_credito': total_tarjeta_credito,
            'total_transferencia': total_transferencia,
            'total_cortesia': 0,
            'total_descuentos': total_descuentos,
            'por_forma_pago': [
                {'forma_pago': 'Efectivo', 'total': resumen['efectivo']['total'], 'cantidad': resumen['efectivo']['cantidad']},
                {'forma_pago': 'Tarjeta Débito', 'total': resumen['tarjeta_debito']['total'], 'cantidad': resumen['tarjeta_debito']['cantidad']},
                {'forma_pago': 'Tarjeta Crédito', 'total': resumen['tarjeta_credito']['total'], 'cantidad': resumen['tarjeta_credito']['cantidad']},
                {'forma_pago': 'Transferencia', 'total': total_transferencia, 'cantidad': resumen['nequi']['cantidad'] + resumen['daviplata']['cantidad'] + resumen['pse']['cantidad'] + resumen['qr_breb']['cantidad']},
            ]
        }

    def _resumen_en_ceros(self, fecha: date) -> Dict:
        return {
            'fecha': str(fecha),
            'total_ventas': 0,
            'total_efectivo_sistema': 0,
            'total_tarjeta_debito': 0,
            'total_tarjeta_credito': 0,
            'total_transferencia': 0,
            'total_cortesia': 0,
            'total_descuentos': 0,
            'por_forma_pago': [
                {'forma_pago': 'Efectivo', 'total': 0, 'cantidad': 0},
                {'forma_pago': 'Tarjeta Debito', 'total': 0, 'cantidad': 0},
                {'forma_pago': 'Tarjeta Credito', 'total': 0, 'cantidad': 0},
                {'forma_pago': 'Transferencia', 'total': 0, 'cantidad': 0},
            ],
        }
    
    async def ejecutar_cierre(
        self,
        fecha: date,
        total_efectivo_contado: float,
        cajero_id: int,
        observaciones: Optional[str] = None,
        fondo_inicial: float = 0,
    ) -> CierreCajaORM:
        """Ejecuta el cierre de caja y lo guarda en la BD.
        
        Args:
            fecha: Fecha del cierre
            total_efectivo_contado: Total contado físicamente
            cajero_id: ID del usuario que realiza el cierre
            observaciones: Observaciones opcionales
            
        Returns:
            Objeto CierreCajaORM creado
        """
        cierre_existente = await self.db.execute(
            select(CierreCajaORM.id).where(
                CierreCajaORM.fecha == fecha,
                CierreCajaORM.restaurante_id == self.restaurante_id,
            )
        )
        if cierre_existente.scalar_one_or_none() is not None:
            raise ValueError(f"Ya existe un cierre de caja para la fecha {fecha}")

        # Obtener resumen
        resumen = await self.obtener_resumen_caja(fecha)

        total_efectivo_sistema = resumen['total_efectivo_sistema']

        # Crear registro de cierre
        cierre = CierreCajaORM(
            restaurante_id=self.restaurante_id,
            fecha=fecha,
            cajero_id=cajero_id,
            total_ventas=resumen['total_ventas'],
            total_efectivo_sistema=int(total_efectivo_sistema),
            total_efectivo_contado=int(total_efectivo_contado),
            total_tarjeta=int(resumen['total_tarjeta_debito'] + resumen['total_tarjeta_credito']),
            total_transferencia=int(resumen['total_transferencia']),
            total_cortesia=0,
            total_descuentos=int(resumen['total_descuentos']),
            fondo_inicial=int(fondo_inicial),
            observaciones=observaciones,
            firmado_at=datetime.utcnow(),
        )
        
        self.db.add(cierre)
        await self.db.commit()
        await self.db.refresh(cierre)
        
        return cierre
