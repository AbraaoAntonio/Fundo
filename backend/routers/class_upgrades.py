import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.class_upgrades import Class_upgradesService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/class_upgrades", tags=["class_upgrades"])


# ---------- Pydantic Schemas ----------
class Class_upgradesData(BaseModel):
    """Entity data schema (for create/update)"""
    profile_id: int = None
    from_class: str = None
    to_class: str = None
    status: str = None
    payments_in_new_class: int = None
    requested_at: str = None
    activated_at: str = None


class Class_upgradesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    profile_id: Optional[int] = None
    from_class: Optional[str] = None
    to_class: Optional[str] = None
    status: Optional[str] = None
    payments_in_new_class: Optional[int] = None
    requested_at: Optional[str] = None
    activated_at: Optional[str] = None


class Class_upgradesResponse(BaseModel):
    """Entity response schema"""
    id: int
    user_id: str
    profile_id: Optional[int] = None
    from_class: Optional[str] = None
    to_class: Optional[str] = None
    status: Optional[str] = None
    payments_in_new_class: Optional[int] = None
    requested_at: Optional[str] = None
    activated_at: Optional[str] = None

    class Config:
        from_attributes = True


class Class_upgradesListResponse(BaseModel):
    """List response schema"""
    items: List[Class_upgradesResponse]
    total: int
    skip: int
    limit: int


class Class_upgradesBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Class_upgradesData]


class Class_upgradesBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Class_upgradesUpdateData


class Class_upgradesBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Class_upgradesBatchUpdateItem]


class Class_upgradesBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Class_upgradesListResponse)
async def query_class_upgradess(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query class_upgradess with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying class_upgradess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Class_upgradesService(db)
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
        logger.debug(f"Found {result['total']} class_upgradess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying class_upgradess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Class_upgradesListResponse)
async def query_class_upgradess_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query class_upgradess with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying class_upgradess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Class_upgradesService(db)
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
        logger.debug(f"Found {result['total']} class_upgradess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying class_upgradess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Class_upgradesResponse)
async def get_class_upgrades(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single class_upgrades by ID (user can only see their own records)"""
    logger.debug(f"Fetching class_upgrades with id: {id}, fields={fields}")
    
    service = Class_upgradesService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Class_upgrades with id {id} not found")
            raise HTTPException(status_code=404, detail="Class_upgrades not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching class_upgrades {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Class_upgradesResponse, status_code=201)
async def create_class_upgrades(
    data: Class_upgradesData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new class_upgrades"""
    logger.debug(f"Creating new class_upgrades with data: {data}")
    
    service = Class_upgradesService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create class_upgrades")
        
        logger.info(f"Class_upgrades created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating class_upgrades: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating class_upgrades: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Class_upgradesResponse], status_code=201)
async def create_class_upgradess_batch(
    request: Class_upgradesBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple class_upgradess in a single request"""
    logger.debug(f"Batch creating {len(request.items)} class_upgradess")
    
    service = Class_upgradesService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} class_upgradess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Class_upgradesResponse])
async def update_class_upgradess_batch(
    request: Class_upgradesBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple class_upgradess in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} class_upgradess")
    
    service = Class_upgradesService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} class_upgradess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Class_upgradesResponse)
async def update_class_upgrades(
    id: int,
    data: Class_upgradesUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing class_upgrades (requires ownership)"""
    logger.debug(f"Updating class_upgrades {id} with data: {data}")

    service = Class_upgradesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Class_upgrades with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Class_upgrades not found")
        
        logger.info(f"Class_upgrades {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating class_upgrades {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating class_upgrades {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_class_upgradess_batch(
    request: Class_upgradesBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple class_upgradess by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} class_upgradess")
    
    service = Class_upgradesService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} class_upgradess successfully")
        return {"message": f"Successfully deleted {deleted_count} class_upgradess", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_class_upgrades(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single class_upgrades by ID (requires ownership)"""
    logger.debug(f"Deleting class_upgrades with id: {id}")
    
    service = Class_upgradesService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Class_upgrades with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Class_upgrades not found")
        
        logger.info(f"Class_upgrades {id} deleted successfully")
        return {"message": "Class_upgrades deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting class_upgrades {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")