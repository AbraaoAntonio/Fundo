import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.requests import RequestsService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/requests", tags=["requests"])


# ---------- Pydantic Schemas ----------
class RequestsData(BaseModel):
    """Entity data schema (for create/update)"""
    profile_id: int = None
    request_type: str = None
    requested_amount: float = None
    approved_amount: float = None
    status: str = None
    payout_type: str = None
    payout_recipient_name: str = None
    payout_recipient_account: str = None
    description: str = None
    admin_notes: str = None
    created_at: str = None
    updated_at: str = None


class RequestsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    profile_id: Optional[int] = None
    request_type: Optional[str] = None
    requested_amount: Optional[float] = None
    approved_amount: Optional[float] = None
    status: Optional[str] = None
    payout_type: Optional[str] = None
    payout_recipient_name: Optional[str] = None
    payout_recipient_account: Optional[str] = None
    description: Optional[str] = None
    admin_notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RequestsResponse(BaseModel):
    """Entity response schema"""
    id: int
    user_id: str
    profile_id: Optional[int] = None
    request_type: Optional[str] = None
    requested_amount: Optional[float] = None
    approved_amount: Optional[float] = None
    status: Optional[str] = None
    payout_type: Optional[str] = None
    payout_recipient_name: Optional[str] = None
    payout_recipient_account: Optional[str] = None
    description: Optional[str] = None
    admin_notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class RequestsListResponse(BaseModel):
    """List response schema"""
    items: List[RequestsResponse]
    total: int
    skip: int
    limit: int


class RequestsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[RequestsData]


class RequestsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: RequestsUpdateData


class RequestsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[RequestsBatchUpdateItem]


class RequestsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=RequestsListResponse)
async def query_requestss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query requestss with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying requestss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = RequestsService(db)
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
        logger.debug(f"Found {result['total']} requestss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying requestss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=RequestsListResponse)
async def query_requestss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query requestss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying requestss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = RequestsService(db)
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
        logger.debug(f"Found {result['total']} requestss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying requestss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=RequestsResponse)
async def get_requests(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single requests by ID (user can only see their own records)"""
    logger.debug(f"Fetching requests with id: {id}, fields={fields}")
    
    service = RequestsService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Requests with id {id} not found")
            raise HTTPException(status_code=404, detail="Requests not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching requests {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=RequestsResponse, status_code=201)
async def create_requests(
    data: RequestsData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new requests"""
    logger.debug(f"Creating new requests with data: {data}")
    
    service = RequestsService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create requests")
        
        logger.info(f"Requests created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating requests: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating requests: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[RequestsResponse], status_code=201)
async def create_requestss_batch(
    request: RequestsBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple requestss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} requestss")
    
    service = RequestsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} requestss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[RequestsResponse])
async def update_requestss_batch(
    request: RequestsBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple requestss in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} requestss")
    
    service = RequestsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} requestss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=RequestsResponse)
async def update_requests(
    id: int,
    data: RequestsUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing requests (requires ownership)"""
    logger.debug(f"Updating requests {id} with data: {data}")

    service = RequestsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Requests with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Requests not found")
        
        logger.info(f"Requests {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating requests {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating requests {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_requestss_batch(
    request: RequestsBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple requestss by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} requestss")
    
    service = RequestsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} requestss successfully")
        return {"message": f"Successfully deleted {deleted_count} requestss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_requests(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single requests by ID (requires ownership)"""
    logger.debug(f"Deleting requests with id: {id}")
    
    service = RequestsService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Requests with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Requests not found")
        
        logger.info(f"Requests {id} deleted successfully")
        return {"message": "Requests deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting requests {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")