from fastapi import APIRouter
router = APIRouter()

@router.get("/tasks/today")
async def tasks_today():
    return {"tasks": [], "formatted": "No tasks yet. Add them at locusapp.online"}

@router.post("/tasks")
async def create_task(task: dict):
    return {"status": "ok", "message": "Task created"}
