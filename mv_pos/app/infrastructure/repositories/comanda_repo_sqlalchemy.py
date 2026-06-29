from __future__ import annotations
from sqlalchemy import insert, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.infrastructure.database.models.comanda import ComandaORM


class ComandaRepoSQLAlchemy:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def crear(self, orden_id: int, mesa_id: int | None, contenido: str, file_path: str | None = None) -> ComandaORM:
        stmt = insert(ComandaORM).values(
            orden_id=orden_id,
            mesa_id=mesa_id,
            contenido=contenido,
            estado='pending',
            file_path=file_path,
        )
        result = await self.session.execute(stmt)
        await self.session.commit()

        # Fetch the created row
        query = select(ComandaORM).where(ComandaORM.orden_id == orden_id).order_by(ComandaORM.id.desc()).limit(1)
        res = await self.session.execute(query)
        return res.scalar_one()

    async def obtener_por_id(self, comanda_id: int) -> ComandaORM | None:
        stmt = select(ComandaORM).where(ComandaORM.id == comanda_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def actualizar_estado(self, comanda_id: int, estado: str, printed_at=None, file_path: str | None = None) -> None:
        stmt = select(ComandaORM).where(ComandaORM.id == comanda_id)
        res = await self.session.execute(stmt)
        comanda = res.scalar_one_or_none()
        if comanda is None:
            return
        comanda.estado = estado
        if printed_at is not None:
            comanda.printed_at = printed_at
        if file_path is not None:
            comanda.file_path = file_path
        self.session.add(comanda)
        await self.session.commit()
