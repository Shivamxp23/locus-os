from app.workers.celery_app import app

@app.task(queue="engine2")
def run_graphrag_crawl(user_id: str):
    pass
