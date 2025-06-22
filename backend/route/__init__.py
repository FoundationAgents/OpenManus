from fastapi import APIRouter

from backend.route.tasks import router as tasks_router


router = APIRouter()

router.include_router(tasks_router)
