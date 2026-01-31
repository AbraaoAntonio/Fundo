import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.payouts import PayoutsService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/payouts", tags=["payouts"])


# ---------- Pydantic Schemas ----------
class PayoutsData(BaseModel):
    """Entity data schema (for create/update)"""
    request_id: int = None
    amount: float = None
    recipient_type: str = None
    recipient_name: str = None
    recipient_account: str = None
    status: str = None
    stripe_payout_id: str = None
    processed_at: str = None
    created_at: str = None


class PayoutsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    request_id: Optional[int] = None
    amount: Optional[float] = None
    recipient_type: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_account: Optional[str] = None
    status: Optional[str] = None
    stripe_payout_id: Optional[str] = None
    processed_at: Optional[str] = None
    created_at: Optional[str] = None


class PayoutsResponse(BaseModel):
    """Entity response schema"""
    id: int
    user_id: str
    request_id: Optional[int] = None
    amount: Optional[float] = None
    recipient_type: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_account: Optional[str] = None
    status: Optional[str] = None
    stripe_payout_id: Optional[str] = None
    processed_at: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class PayoutsListResponse(BaseModel):
    """List response schema"""
    items: List[PayoutsResponse]
    total: int
    skip: int
    limit: int


class PayoutsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[PayoutsData]


class PayoutsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: PayoutsUpdateData


class PayoutsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[PayoutsBatchUpdateItem]


class PayoutsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=PayoutsListResponse)
async def query_payoutss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query payoutss with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying payoutss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = PayoutsService(db)
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
        logger.debug(f"Found {result['total']} payoutss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying payoutss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=PayoutsListResponse)
async def query_payoutss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query payoutss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying payoutss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = PayoutsService(db)
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
        logger.debug(f"Found {result['total']} payoutss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying payoutss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=PayoutsResponse)
async def get_payouts(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single payouts by ID (user can only see their own records)"""
    logger.debug(f"Fetching payouts with id: {id}, fields={fields}")
    
    service = PayoutsService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Payouts with id {id} not found")
            raise HTTPException(status_code=404, detail="Payouts not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching payouts {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=PayoutsResponse, status_code=201)
async def create_payouts(
    data: PayoutsData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new payouts"""
    logger.debug(f"Creating new payouts with data: {data}")
    
    service = PayoutsService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create payouts")
        
        logger.info(f"Payouts created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating payouts: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating payouts: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[PayoutsResponse], status_code=201)
async def create_payoutss_batch(
    request: PayoutsBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple payoutss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} payoutss")
    
    service = PayoutsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} payoutss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[PayoutsResponse])
async def update_payoutss_batch(
    request: PayoutsBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple payoutss in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} payoutss")
    
    service = PayoutsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} payoutss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=PayoutsResponse)
async def update_payouts(
    id: int,
    data: PayoutsUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing payouts (requires ownership)"""
    logger.debug(f"Updating payouts {id} with data: {data}")

    service = PayoutsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Payouts with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Payouts not found")
        
        logger.info(f"Payouts {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating payouts {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating payouts {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_payoutss_batch(
    request: PayoutsBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple payoutss by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} payoutss")
    
    service = PayoutsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} payoutss successfully")
        return {"message": f"Successfully deleted {deleted_count} payoutss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_payouts(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single payouts by ID (requires ownership)"""
    logger.debug(f"Deleting payouts with id: {id}")
    
    service = PayoutsService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Payouts with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Payouts not found")
        
        logger.info(f"Payouts {id} deleted successfully")
        return {"message": "Payouts deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting payouts {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")