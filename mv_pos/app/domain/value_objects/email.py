from __future__ import annotations
import re

class Email:
    _EMAIL_PATTERN = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

    def __init__(self, value: str) -> None:
        if not self._EMAIL_PATTERN.match(value):
            raise ValueError('Email inválido')
        self.value = value.lower().strip()

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Email) and self.value == other.value
