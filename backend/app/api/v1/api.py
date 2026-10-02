from fastapi import APIRouter
from app.api.v1.projects import router as projects_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.calendar_gantt import router as calendar_gantt_router
from app.api.v1.reports import router as reports_router

api_router = APIRouter()

api_router.include_router(projects_router)
api_router.include_router(tasks_router)
api_router.include_router(calendar_gantt_router)
api_router.include_router(reports_router)
