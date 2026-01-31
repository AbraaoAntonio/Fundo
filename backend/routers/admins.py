import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.admins import AdminsService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/admins", tags=["admins"])


# ---------- Pydantic Schemas ----------
class AdminsData(BaseModel):
    """Entity data schema (for create/update)"""
    email: str
    full_name: str
    role: str
    created_at: str


class AdminsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[str] = None
    created_at: Optional[str] = None


class AdminsResponse(BaseModel):
    """Entity response schema"""
    id: int
    user_id: str
    email: str
    full_name: str
    role: str
    created_at: str

    class Config:
        from_attributes = True


class AdminsListResponse(BaseModel):
    """List response schema"""
    items: List[AdminsResponse]
    total: int
    skip: int
    limit: int


class AdminsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[AdminsData]


class AdminsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: AdminsUpdateData


class AdminsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[AdminsBatchUpdateItem]


class AdminsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=AdminsListResponse)
async def query_adminss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query adminss with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying adminss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = AdminsService(db)
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
        logger.debug(f"Found {result['total']} adminss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying adminss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=AdminsListResponse)
async def query_adminss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query adminss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying adminss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = AdminsService(db)
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
        logger.debug(f"Found {result['total']} adminss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying adminss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=AdminsResponse)
async def get_admins(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single admins by ID (user can only see their own records)"""
    logger.debug(f"Fetching admins with id: {id}, fields={fields}")
    
    service = AdminsService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Admins with id {id} not found")
            raise HTTPException(status_code=404, detail="Admins not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching admins {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=AdminsResponse, status_code=201)
async def create_admins(
    data: AdminsData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new admins"""
    logger.debug(f"Creating new admins with data: {data}")
    
    service = AdminsService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create admins")
        
        logger.info(f"Admins created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating admins: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating admins: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[AdminsResponse], status_code=201)
async def create_adminss_batch(
    request: AdminsBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple adminss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} adminss")
    
    service = AdminsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} adminss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[AdminsResponse])
async def update_adminss_batch(
    request: AdminsBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple adminss in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} adminss")
    
    service = AdminsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} adminss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=AdminsResponse)
async def update_admins(
    id: int,
    data: AdminsUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing admins (requires ownership)"""
    logger.debug(f"Updating admins {id} with data: {data}")

    service = AdminsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Admins with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Admins not found")
        
        logger.info(f"Admins {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating admins {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating admins {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_adminss_batch(
    request: AdminsBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple adminss by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} adminss")
    
    service = AdminsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} adminss successfully")
        return {"message": f"Successfully deleted {deleted_count} adminss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_admins(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single admins by ID (requires ownership)"""
    logger.debug(f"Deleting admins with id: {id}")
    
    service = AdminsService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Admins with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Admins not found")
        
        logger.info(f"Admins {id} deleted successfully")
        return {"message": "Admins deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting admins {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")