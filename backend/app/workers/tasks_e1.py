from app.workers.celery_app import app

@app.task(queue="engine1")
def process_behavioral_event(event_data: dict):
    pass
