from __future__ import annotations

# Alias — shared DB approach uses a single Base for all models including restaurantes.
from app.infrastructure.database.base import Base as ControlBase  # noqa: F401
