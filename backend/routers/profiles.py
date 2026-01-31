import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.profiles import ProfilesService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/profiles", tags=["profiles"])


# ---------- Pydantic Schemas ----------
class ProfilesData(BaseModel):
    """Entity data schema (for create/update)"""
    full_name: str
    phone: str
    membership_class: str
    account_status: str
    consecutive_months_paid: int = None
    months_late: int = None
    stripe_subscription_id: str = None
    created_at: str
    updated_at: str


class ProfilesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    full_name: Optional[str] = None
    phone: Optional[str] = None
    membership_class: Optional[str] = None
    account_status: Optional[str] = None
    consecutive_months_paid: Optional[int] = None
    months_late: Optional[int] = None
    stripe_subscription_id: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ProfilesResponse(BaseModel):
    """Entity response schema"""
    id: int
    user_id: str
    full_name: str
    phone: str
    membership_class: str
    account_status: str
    consecutive_months_paid: Optional[int] = None
    months_late: Optional[int] = None
    stripe_subscription_id: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ProfilesListResponse(BaseModel):
    """List response schema"""
    items: List[ProfilesResponse]
    total: int
    skip: int
    limit: int


class ProfilesBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[ProfilesData]


class ProfilesBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: ProfilesUpdateData


class ProfilesBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[ProfilesBatchUpdateItem]


class ProfilesBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=ProfilesListResponse)
async def query_profiless(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query profiless with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying profiless: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = ProfilesService(db)
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
        logger.debug(f"Found {result['total']} profiless")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying profiless: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=ProfilesListResponse)
async def query_profiless_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query profiless with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying profiless: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = ProfilesService(db)
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
        logger.debug(f"Found {result['total']} profiless")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying profiless: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=ProfilesResponse)
async def get_profiles(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single profiles by ID (user can only see their own records)"""
    logger.debug(f"Fetching profiles with id: {id}, fields={fields}")
    
    service = ProfilesService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Profiles with id {id} not found")
            raise HTTPException(status_code=404, detail="Profiles not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching profiles {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=ProfilesResponse, status_code=201)
async def create_profiles(
    data: ProfilesData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new profiles"""
    logger.debug(f"Creating new profiles with data: {data}")
    
    service = ProfilesService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create profiles")
        
        logger.info(f"Profiles created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating profiles: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating profiles: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[ProfilesResponse], status_code=201)
async def create_profiless_batch(
    request: ProfilesBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple profiless in a single request"""
    logger.debug(f"Batch creating {len(request.items)} profiless")
    
    service = ProfilesService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} profiless successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[ProfilesResponse])
async def update_profiless_batch(
    request: ProfilesBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple profiless in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} profiless")
    
    service = ProfilesService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} profiless successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=ProfilesResponse)
async def update_profiles(
    id: int,
    data: ProfilesUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing profiles (requires ownership)"""
    logger.debug(f"Updating profiles {id} with data: {data}")

    service = ProfilesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Profiles with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Profiles not found")
        
        logger.info(f"Profiles {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating profiles {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating profiles {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_profiless_batch(
    request: ProfilesBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple profiless by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} profiless")
    
    service = ProfilesService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} profiless successfully")
        return {"message": f"Successfully deleted {deleted_count} profiless", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_profiles(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single profiles by ID (requires ownership)"""
    logger.debug(f"Deleting profiles with id: {id}")
    
    service = ProfilesService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Profiles with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Profiles not found")
        
        logger.info(f"Profiles {id} deleted successfully")
        return {"message": "Profiles deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting profiles {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")