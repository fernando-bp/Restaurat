from __future__ import annotations

# Alias — shared DB approach uses a single engine/session for everything.
from app.infrastructure.database.connection import engine as control_engine  # noqa: F401
from app.infrastructure.database.connection import async_session as control_async_session  # noqa: F401
