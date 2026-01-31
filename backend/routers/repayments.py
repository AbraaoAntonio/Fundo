import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.repayments import RepaymentsService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/repayments", tags=["repayments"])


# ---------- Pydantic Schemas ----------
class RepaymentsData(BaseModel):
    """Entity data schema (for create/update)"""
    request_id: int = None
    total_to_repay: float = None
    installments: int = None
    installment_amount: float = None
    paid_installments: int = None
    status: str = None
    next_due_date: str = None
    created_at: str = None
    updated_at: str = None


class RepaymentsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    request_id: Optional[int] = None
    total_to_repay: Optional[float] = None
    installments: Optional[int] = None
    installment_amount: Optional[float] = None
    paid_installments: Optional[int] = None
    status: Optional[str] = None
    next_due_date: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RepaymentsResponse(BaseModel):
    """Entity response schema"""
    id: int
    user_id: str
    request_id: Optional[int] = None
    total_to_repay: Optional[float] = None
    installments: Optional[int] = None
    installment_amount: Optional[float] = None
    paid_installments: Optional[int] = None
    status: Optional[str] = None
    next_due_date: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class RepaymentsListResponse(BaseModel):
    """List response schema"""
    items: List[RepaymentsResponse]
    total: int
    skip: int
    limit: int


class RepaymentsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[RepaymentsData]


class RepaymentsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: RepaymentsUpdateData


class RepaymentsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[RepaymentsBatchUpdateItem]


class RepaymentsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=RepaymentsListResponse)
async def query_repaymentss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query repaymentss with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying repaymentss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = RepaymentsService(db)
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
        logger.debug(f"Found {result['total']} repaymentss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying repaymentss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=RepaymentsListResponse)
async def query_repaymentss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query repaymentss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying repaymentss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = RepaymentsService(db)
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
        logger.debug(f"Found {result['total']} repaymentss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying repaymentss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=RepaymentsResponse)
async def get_repayments(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single repayments by ID (user can only see their own records)"""
    logger.debug(f"Fetching repayments with id: {id}, fields={fields}")
    
    service = RepaymentsService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Repayments with id {id} not found")
            raise HTTPException(status_code=404, detail="Repayments not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching repayments {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=RepaymentsResponse, status_code=201)
async def create_repayments(
    data: RepaymentsData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new repayments"""
    logger.debug(f"Creating new repayments with data: {data}")
    
    service = RepaymentsService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create repayments")
        
        logger.info(f"Repayments created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating repayments: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating repayments: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[RepaymentsResponse], status_code=201)
async def create_repaymentss_batch(
    request: RepaymentsBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple repaymentss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} repaymentss")
    
    service = RepaymentsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} repaymentss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[RepaymentsResponse])
async def update_repaymentss_batch(
    request: RepaymentsBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple repaymentss in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} repaymentss")
    
    service = RepaymentsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} repaymentss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=RepaymentsResponse)
async def update_repayments(
    id: int,
    data: RepaymentsUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing repayments (requires ownership)"""
    logger.debug(f"Updating repayments {id} with data: {data}")

    service = RepaymentsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Repayments with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Repayments not found")
        
        logger.info(f"Repayments {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating repayments {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating repayments {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_repaymentss_batch(
    request: RepaymentsBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple repaymentss by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} repaymentss")
    
    service = RepaymentsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} repaymentss successfully")
        return {"message": f"Successfully deleted {deleted_count} repaymentss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_repayments(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single repayments by ID (requires ownership)"""
    logger.debug(f"Deleting repayments with id: {id}")
    
    service = RepaymentsService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Repayments with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Repayments not found")
        
        logger.info(f"Repayments {id} deleted successfully")
        return {"message": "Repayments deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting repayments {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")