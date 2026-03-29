import os
from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery("locus", broker=redis_url, backend=redis_url,
    include=["app.workers.tasks_e1", "app.workers.tasks_e2", "app.workers.tasks_e3"])

app.conf.update(
    task_serializer="json", result_serializer="json",
    accept_content=["json"], timezone="Asia/Kolkata", enable_utc=True,
    task_routes={
        "app.workers.tasks_e1.*": {"queue": "engine1"},
        "app.workers.tasks_e2.*": {"queue": "engine2"},
        "app.workers.tasks_e3.*": {"queue": "engine3"},
    }
)
