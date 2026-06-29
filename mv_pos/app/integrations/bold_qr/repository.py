from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.bold_qr.models import BoldPaymentIntentORM


class BoldQrRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, intent: BoldPaymentIntentORM) -> BoldPaymentIntentORM:
        self.session.add(intent)
        await self.session.commit()
        await self.session.refresh(intent)
        return intent

    async def get_by_id(self, intent_id: int) -> BoldPaymentIntentORM | None:
        result = await self.session.execute(
            select(BoldPaymentIntentORM).where(BoldPaymentIntentORM.id == intent_id)
        )
        return result.scalar_one_or_none()

    async def get_by_reference(self, reference: str) -> BoldPaymentIntentORM | None:
        result = await self.session.execute(
            select(BoldPaymentIntentORM).where(BoldPaymentIntentORM.referencia == reference)
        )
        return result.scalar_one_or_none()

    async def get_by_bold_payment_id(self, bold_payment_id: str) -> BoldPaymentIntentORM | None:
        result = await self.session.execute(
            select(BoldPaymentIntentORM).where(BoldPaymentIntentORM.bold_payment_id == bold_payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_webhook_id(self, webhook_id: str) -> BoldPaymentIntentORM | None:
        result = await self.session.execute(
            select(BoldPaymentIntentORM).where(BoldPaymentIntentORM.webhook_id == webhook_id)
        )
        return result.scalar_one_or_none()

    async def save(self, intent: BoldPaymentIntentORM) -> BoldPaymentIntentORM:
        await self.session.commit()
        await self.session.refresh(intent)
        return intent
