from __future__ import annotations
import asyncio
from datetime import datetime
from app.worker.celery_app import get_celery

celery = get_celery()


@celery.task(bind=True, name='mvpos.enviar_comanda', acks_late=True)
def enviar_comanda(self, comanda_id: int) -> dict:
    """Task robusta que marca la comanda como enviada/imprimida.

    Ejecuta una función async dentro de un bucle para usar el AsyncSession.
    """
    try:
        return asyncio.run(_enviar_comanda_async(comanda_id))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=5, max_retries=3)


async def _enviar_comanda_async(comanda_id: int) -> dict:
    from datetime import datetime
    from app.infrastructure.database import AsyncSessionLocal
    from app.infrastructure.database.models.comanda import ComandaORM

    async with AsyncSessionLocal() as session:
        # Cargar la comanda
        comanda = await session.get(ComandaORM, comanda_id)
        if comanda is None:
            return {'status': 'not_found', 'comanda_id': comanda_id}

        # Aquí se implementaría la lógica de envío/impresión (ESC/POS, API de impresora, etc.)
        # Por ahora, simulamos el envío y actualizamos estado a 'printed'
        comanda.estado = 'printed'
        comanda.printed_at = datetime.utcnow()
        session.add(comanda)
        await session.commit()

        return {'status': 'printed', 'comanda_id': comanda_id, 'printed_at': comanda.printed_at.isoformat()}
