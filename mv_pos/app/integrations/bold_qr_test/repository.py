from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.bold_qr_test.models import BoldQrPagoIndependienteORM


class BoldQrTestRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, payment: BoldQrPagoIndependienteORM) -> BoldQrPagoIndependienteORM:
        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def get_by_id(self, payment_id: int) -> BoldQrPagoIndependienteORM | None:
        result = await self.session.execute(
            select(BoldQrPagoIndependienteORM).where(BoldQrPagoIndependienteORM.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_reference(self, reference: str) -> BoldQrPagoIndependienteORM | None:
        result = await self.session.execute(
            select(BoldQrPagoIndependienteORM).where(BoldQrPagoIndependienteORM.referencia == reference)
        )
        return result.scalar_one_or_none()

    async def get_by_bold_payment_id(self, bold_payment_id: str) -> BoldQrPagoIndependienteORM | None:
        result = await self.session.execute(
            select(BoldQrPagoIndependienteORM).where(BoldQrPagoIndependienteORM.bold_payment_id == bold_payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_webhook_id(self, webhook_id: str) -> BoldQrPagoIndependienteORM | None:
        result = await self.session.execute(
            select(BoldQrPagoIndependienteORM).where(BoldQrPagoIndependienteORM.webhook_id == webhook_id)
        )
        return result.scalar_one_or_none()

    async def save(self, payment: BoldQrPagoIndependienteORM) -> BoldQrPagoIndependienteORM:
        await self.session.commit()
        await self.session.refresh(payment)
        return payment
