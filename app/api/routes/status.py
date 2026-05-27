from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.status import GlobalStatus
from app.services import status_service

router = APIRouter(tags=["status"])


@router.get("/status", response_model=GlobalStatus)
async def get_status(db: AsyncSession = Depends(get_db)) -> GlobalStatus:
    """Retourne l'état consolidé courant de toutes les machines."""
    return await status_service.get_consolidated_status(db)

