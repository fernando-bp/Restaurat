from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TransferirMesaRequestDTO:
    """DTO para transferir una mesa a otro mesero"""
    nuevo_mesero_id: int


@dataclass
class TransferirMesaResponseDTO:
    """Respuesta de transferencia de mesa"""
    orden_id: int
    mesa_id: int
    mesa_numero: str
    mesero_id_anterior: int
    mesero_anterior_nombre: str
    mesero_id_nuevo: int
    mesero_nuevo_nombre: str
    hora_transferencia: datetime
    mensaje: str


@dataclass
class UnirMesasRequestDTO:
    """DTO para unir dos mesas en una sola orden"""
    mesa_origen_id: int  # Mesa cuyos items se copiarán
    mesa_destino_id: int  # Mesa que recibirá los items


@dataclass
class UnirMesasResponseDTO:
    """Respuesta de unión de mesas"""
    orden_destino_id: int
    mesa_destino_id: int
    mesa_destino_numero: str
    orden_origen_id: int  # La que fue eliminada
    mesa_origen_id: int
    mesa_origen_numero: str
    num_items_consolidados: int
    nuevo_total_comensales: int
    hora_union: datetime
    mensaje: str
