from __future__ import annotations

# Stub — tenant routing is done via restaurante_id column on every table,
# not via separate databases. This module is kept for import compatibility.


class _NoOpRegistry:
    def register(self, *args, **kwargs) -> None:
        pass

    def get_engine(self, *args, **kwargs):
        return None

    def get_id_by_slug(self, *args, **kwargs):
        return None

    def make_session_factory(self, *args, **kwargs):
        return None

    async def close_all(self) -> None:
        pass


tenant_registry = _NoOpRegistry()
