import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.success_stories import Success_storiesService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/success_stories", tags=["success_stories"])


# ---------- Pydantic Schemas ----------
class Success_storiesData(BaseModel):
    """Entity data schema (for create/update)"""
    member_name: str
    story: str
    amount_received: float
    is_published: bool
    created_at: str


class Success_storiesUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    member_name: Optional[str] = None
    story: Optional[str] = None
    amount_received: Optional[float] = None
    is_published: Optional[bool] = None
    created_at: Optional[str] = None


class Success_storiesResponse(BaseModel):
    """Entity response schema"""
    id: int
    member_name: str
    story: str
    amount_received: float
    is_published: bool
    created_at: str

    class Config:
        from_attributes = True


class Success_storiesListResponse(BaseModel):
    """List response schema"""
    items: List[Success_storiesResponse]
    total: int
    skip: int
    limit: int


class Success_storiesBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Success_storiesData]


class Success_storiesBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Success_storiesUpdateData


class Success_storiesBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Success_storiesBatchUpdateItem]


class Success_storiesBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Success_storiesListResponse)
async def query_success_storiess(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query success_storiess with filtering, sorting, and pagination"""
    logger.debug(f"Querying success_storiess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Success_storiesService(db)
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
        )
        logger.debug(f"Found {result['total']} success_storiess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying success_storiess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Success_storiesListResponse)
async def query_success_storiess_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query success_storiess with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying success_storiess: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Success_storiesService(db)
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
        logger.debug(f"Found {result['total']} success_storiess")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying success_storiess: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Success_storiesResponse)
async def get_success_stories(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single success_stories by ID"""
    logger.debug(f"Fetching success_stories with id: {id}, fields={fields}")
    
    service = Success_storiesService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Success_stories with id {id} not found")
            raise HTTPException(status_code=404, detail="Success_stories not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching success_stories {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Success_storiesResponse, status_code=201)
async def create_success_stories(
    data: Success_storiesData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new success_stories"""
    logger.debug(f"Creating new success_stories with data: {data}")
    
    service = Success_storiesService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create success_stories")
        
        logger.info(f"Success_stories created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating success_stories: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating success_stories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Success_storiesResponse], status_code=201)
async def create_success_storiess_batch(
    request: Success_storiesBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple success_storiess in a single request"""
    logger.debug(f"Batch creating {len(request.items)} success_storiess")
    
    service = Success_storiesService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} success_storiess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Success_storiesResponse])
async def update_success_storiess_batch(
    request: Success_storiesBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple success_storiess in a single request"""
    logger.debug(f"Batch updating {len(request.items)} success_storiess")
    
    service = Success_storiesService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} success_storiess successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Success_storiesResponse)
async def update_success_stories(
    id: int,
    data: Success_storiesUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing success_stories"""
    logger.debug(f"Updating success_stories {id} with data: {data}")

    service = Success_storiesService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Success_stories with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Success_stories not found")
        
        logger.info(f"Success_stories {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating success_stories {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating success_stories {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_success_storiess_batch(
    request: Success_storiesBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple success_storiess by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} success_storiess")
    
    service = Success_storiesService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} success_storiess successfully")
        return {"message": f"Successfully deleted {deleted_count} success_storiess", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_success_stories(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single success_stories by ID"""
    logger.debug(f"Deleting success_stories with id: {id}")
    
    service = Success_storiesService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Success_stories with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Success_stories not found")
        
        logger.info(f"Success_stories {id} deleted successfully")
        return {"message": "Success_stories deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting success_stories {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")