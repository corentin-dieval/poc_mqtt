from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> JSONResponse:
    """Liveness probe."""
    return JSONResponse(content={"status": "ok"})

