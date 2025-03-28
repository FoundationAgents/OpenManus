from fastapi import APIRouter

from app.apis.routes.config import router as config_router
from app.apis.routes.tasks import router as tasks_router
from app.apis.routes.workspace import router as workspace_router

router = APIRouter()

router.include_router(config_router)
router.include_router(tasks_router)
router.include_router(workspace_router)
