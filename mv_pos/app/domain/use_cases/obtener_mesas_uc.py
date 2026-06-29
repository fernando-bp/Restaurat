from __future__ import annotations
from typing import Optional
from datetime import datetime

from app.domain.repositories.mesa_repository import MesaRepository
from app.application.dtos.mesa_dto import MesaStatusDTO, MesaMapResponseDTO, MesaListResponseDTO


class ObtenerEstadoMesasUC:
    """Use Case: Obtener estado de todas las mesas en tiempo real (RF-05)"""
    
    def __init__(self, mesa_repo: MesaRepository):
        self.mesa_repo = mesa_repo

    async def execute(self, zona: Optional[str] = None) -> list[MesaStatusDTO]:
        """
        Obtiene el estado actual de todas las mesas desde v_mesas_estado
        
        Args:
            zona: (Opcional) Filtrar por zona específica
            
        Returns:
            Lista de MesaStatusDTO con estado en tiempo real
        """
        mesas_raw = await self.mesa_repo.obtener_estado_mesas(zona=zona)
        
        # Convertir rows a DTOs
        mesas_dto = []
        for mesa in mesas_raw:
            dto = MesaStatusDTO(
                id=mesa['id'],
                numero=mesa['numero'],
                capacidad=mesa['capacidad'],
                zona=mesa.get('zona'),
                estado=mesa['estado'],
                orden_id=mesa.get('orden_id'),
                num_comensales=mesa.get('num_comensales'),
                hora_apertura=mesa.get('hora_apertura'),
                mesero=mesa.get('mesero'),
                total_neto=mesa.get('total_neto'),
            )
            mesas_dto.append(dto)
        
        return mesas_dto


class ObtenerMapaMesasUC:
    """Use Case: Obtener mapa visual de mesas agrupado por zona (RF-05)"""
    
    def __init__(self, mesa_repo: MesaRepository):
        self.mesa_repo = mesa_repo

    async def execute(self, zona: Optional[str] = None) -> MesaMapResponseDTO:
        """
        Obtiene todas las mesas agrupadas por zona, con estadísticas
        Optimizado para renderizar en UI de mapa de mesas
        
        Args:
            zona: (Opcional) Filtrar por zona específica
            
        Returns:
            MesaMapResponseDTO con mapa agrupado y estadísticas
        """
        mesas_raw = await self.mesa_repo.obtener_estado_mesas(zona=zona)
        
        # Convertir a DTOs y agrupar por zona
        mapa: dict[str, list[MesaStatusDTO]] = {}
        estadisticas = {
            'total': 0,
            'ocupadas': 0,
            'reservadas': 0,
            'libres': 0,
        }
        
        for mesa in mesas_raw:
            dto = MesaStatusDTO(
                id=mesa['id'],
                numero=mesa['numero'],
                capacidad=mesa['capacidad'],
                zona=mesa.get('zona'),
                estado=mesa['estado'],
                orden_id=mesa.get('orden_id'),
                num_comensales=mesa.get('num_comensales'),
                hora_apertura=mesa.get('hora_apertura'),
                mesero=mesa.get('mesero'),
                total_neto=mesa.get('total_neto'),
            )
            
            # Agrupar por zona
            zona_key = mesa.get('zona') or 'Sin zona'
            if zona_key not in mapa:
                mapa[zona_key] = []
            mapa[zona_key].append(dto)
            
            # Actualizar estadísticas
            estadisticas['total'] += 1
            if mesa['estado'] == 'ocupada':
                estadisticas['ocupadas'] += 1
            elif mesa['estado'] == 'reservada':
                estadisticas['reservadas'] += 1
            elif mesa['estado'] == 'libre':
                estadisticas['libres'] += 1
        
        return MesaMapResponseDTO(
            timestamp=datetime.utcnow(),
            mapa=mapa,
            total_mesas=estadisticas['total'],
            ocupadas=estadisticas['ocupadas'],
            reservadas=estadisticas['reservadas'],
            libres=estadisticas['libres'],
        )


class ObtenerEstadoMesaUC:
    """Use Case: Obtener estado de una mesa específica en tiempo real (RF-05)"""
    
    def __init__(self, mesa_repo: MesaRepository):
        self.mesa_repo = mesa_repo

    async def execute(self, mesa_id: int) -> MesaStatusDTO | None:
        """
        Obtiene el estado actual de una mesa específica
        
        Args:
            mesa_id: ID de la mesa
            
        Returns:
            MesaStatusDTO o None si no existe
        """
        mesa_raw = await self.mesa_repo.obtener_estado_mesa(mesa_id=mesa_id)
        
        if not mesa_raw:
            return None
        
        return MesaStatusDTO(
            id=mesa_raw['id'],
            numero=mesa_raw['numero'],
            capacidad=mesa_raw['capacidad'],
            zona=mesa_raw.get('zona'),
            estado=mesa_raw['estado'],
            orden_id=mesa_raw.get('orden_id'),
            num_comensales=mesa_raw.get('num_comensales'),
            hora_apertura=mesa_raw.get('hora_apertura'),
            mesero=mesa_raw.get('mesero'),
            total_neto=mesa_raw.get('total_neto'),
        )
