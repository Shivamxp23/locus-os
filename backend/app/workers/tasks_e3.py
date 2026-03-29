from app.workers.celery_app import app

@app.task(queue="engine3")
def generate_schedule(user_id: str):
    pass
