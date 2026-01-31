import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.repayment_installments import Repayment_installmentsService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/repayment_installments", tags=["repayment_installments"])


# ---------- Pydantic Schemas ----------
class Repayment_installmentsData(BaseModel):
    """Entity data schema (for create/update)"""
    repayment_id: int = None
    installment_number: int = None
    amount: float = None
    due_date: str = None
    paid_date: str = None
    status: str = None
    stripe_payment_id: str = None
    created_at: str = None


class Repayment_installmentsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    repayment_id: Optional[int] = None
    installment_number: Optional[int] = None
    amount: Optional[float] = None
    due_date: Optional[str] = None
    paid_date: Optional[str] = None
    status: Optional[str] = None
    stripe_payment_id: Optional[str] = None
    created_at: Optional[str] = None


class Repayment_installmentsResponse(BaseModel):
    """Entity response schema"""
    id: int
    user_id: str
    repayment_id: Optional[int] = None
    installment_number: Optional[int] = None
    amount: Optional[float] = None
    due_date: Optional[str] = None
    paid_date: Optional[str] = None
    status: Optional[str] = None
    stripe_payment_id: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class Repayment_installmentsListResponse(BaseModel):
    """List response schema"""
    items: List[Repayment_installmentsResponse]
    total: int
    skip: int
    limit: int


class Repayment_installmentsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Repayment_installmentsData]


class Repayment_installmentsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Repayment_installmentsUpdateData


class Repayment_installmentsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Repayment_installmentsBatchUpdateItem]


class Repayment_installmentsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Repayment_installmentsListResponse)
async def query_repayment_installmentss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query repayment_installmentss with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying repayment_installmentss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Repayment_installmentsService(db)
    try:
        # Parse query JSON if provided
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")
        
        result = await service.get_list(
            skip=skip, 
            limit=limit,
            query_dict=query_dict,
            sort=sort,
            user_id=str(current_user.id),
        )
        logger.debug(f"Found {result['total']} repayment_installmentss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying repayment_installmentss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Repayment_installmentsListResponse)
async def query_repayment_installmentss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query repayment_installmentss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying repayment_installmentss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Repayment_installmentsService(db)
    try:
        # Parse query JSON if provided
        query_dict = None
        if query:
            try:
                query_dict = json.loads(query)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid query JSON format")

        result = await service.get_list(
            skip=skip,
            limit=limit,
            query_dict=query_dict,
            sort=sort
        )
        logger.debug(f"Found {result['total']} repayment_installmentss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying repayment_installmentss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Repayment_installmentsResponse)
async def get_repayment_installments(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single repayment_installments by ID (user can only see their own records)"""
    logger.debug(f"Fetching repayment_installments with id: {id}, fields={fields}")
    
    service = Repayment_installmentsService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Repayment_installments with id {id} not found")
            raise HTTPException(status_code=404, detail="Repayment_installments not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching repayment_installments {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Repayment_installmentsResponse, status_code=201)
async def create_repayment_installments(
    data: Repayment_installmentsData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new repayment_installments"""
    logger.debug(f"Creating new repayment_installments with data: {data}")
    
    service = Repayment_installmentsService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create repayment_installments")
        
        logger.info(f"Repayment_installments created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating repayment_installments: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating repayment_installments: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Repayment_installmentsResponse], status_code=201)
async def create_repayment_installmentss_batch(
    request: Repayment_installmentsBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple repayment_installmentss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} repayment_installmentss")
    
    service = Repayment_installmentsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} repayment_installmentss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Repayment_installmentsResponse])
async def update_repayment_installmentss_batch(
    request: Repayment_installmentsBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple repayment_installmentss in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} repayment_installmentss")
    
    service = Repayment_installmentsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} repayment_installmentss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Repayment_installmentsResponse)
async def update_repayment_installments(
    id: int,
    data: Repayment_installmentsUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing repayment_installments (requires ownership)"""
    logger.debug(f"Updating repayment_installments {id} with data: {data}")

    service = Repayment_installmentsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Repayment_installments with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Repayment_installments not found")
        
        logger.info(f"Repayment_installments {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating repayment_installments {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating repayment_installments {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_repayment_installmentss_batch(
    request: Repayment_installmentsBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple repayment_installmentss by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} repayment_installmentss")
    
    service = Repayment_installmentsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} repayment_installmentss successfully")
        return {"message": f"Successfully deleted {deleted_count} repayment_installmentss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_repayment_installments(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single repayment_installments by ID (requires ownership)"""
    logger.debug(f"Deleting repayment_installments with id: {id}")
    
    service = Repayment_installmentsService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Repayment_installments with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Repayment_installments not found")
        
        logger.info(f"Repayment_installments {id} deleted successfully")
        return {"message": "Repayment_installments deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting repayment_installments {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")