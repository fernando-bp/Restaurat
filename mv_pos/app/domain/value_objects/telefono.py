from __future__ import annotations
import re

class Telefono:
    _TELEFONO_PATTERN = re.compile(r'^\+?[0-9]{7,15}$')

    def __init__(self, value: str) -> None:
        sanitized = value.strip()
        if not self._TELEFONO_PATTERN.match(sanitized):
            raise ValueError('Teléfono inválido')
        self.value = sanitized

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Telefono) and self.value == other.value
