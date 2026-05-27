from fastapi import APIRouter

from app.api.routes import events, health, status

router = APIRouter()
router.include_router(health.router)
router.include_router(status.router)
router.include_router(events.router)

