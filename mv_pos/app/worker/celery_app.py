from __future__ import annotations
import os
from celery import Celery

BROKER = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
BACKEND = os.getenv('CELERY_RESULT_BACKEND', BROKER)

celery_app = Celery('mv_pos', broker=BROKER, backend=BACKEND)

# Optional basic config; can be extended in production
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)


def get_celery():
    return celery_app
