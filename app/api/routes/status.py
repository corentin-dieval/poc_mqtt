from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.status import ProductStatus # Import ProductStatus
from app.services import status_service

router = APIRouter(tags=["status"])


@router.get("/status/{id_product}", response_model=ProductStatus) # Change response_model to ProductStatus
async def get_product_status(
    id_product: str,
    db: AsyncSession = Depends(get_db)
) -> ProductStatus: # Change return type hint to ProductStatus
    """
    Retourne l'état consolidé courant pour un id_product (stack ou cellule) spécifique.
    Retourne 404 si l'id_product n'est pas trouvé.
    """
    result = await status_service.get_consolidated_status(db, id_product=id_product)
    
    if result is None: # Check if result is None
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with ID '{id_product}' not found or has no associated events."
        )
    
    return result
