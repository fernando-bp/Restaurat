"""Objetos de valor inmutables del dominio MV-POS."""

from app.domain.value_objects.email import Email
from app.domain.value_objects.telefono import Telefono
from app.domain.value_objects.dinero import Dinero
from app.domain.value_objects.money import Money

__all__ = [
    'Email',
    'Telefono',
    'Dinero',
    'Money',
]
