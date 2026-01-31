import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.contributions import ContributionsService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/contributions", tags=["contributions"])


# ---------- Pydantic Schemas ----------
class ContributionsData(BaseModel):
    """Entity data schema (for create/update)"""
    profile_id: int = None
    contribution_type: str = None
    amount: float = None
    status: str = None
    payment_date: str = None
    stripe_payment_id: str = None
    created_at: str = None


class ContributionsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    profile_id: Optional[int] = None
    contribution_type: Optional[str] = None
    amount: Optional[float] = None
    status: Optional[str] = None
    payment_date: Optional[str] = None
    stripe_payment_id: Optional[str] = None
    created_at: Optional[str] = None


class ContributionsResponse(BaseModel):
    """Entity response schema"""
    id: int
    user_id: str
    profile_id: Optional[int] = None
    contribution_type: Optional[str] = None
    amount: Optional[float] = None
    status: Optional[str] = None
    payment_date: Optional[str] = None
    stripe_payment_id: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ContributionsListResponse(BaseModel):
    """List response schema"""
    items: List[ContributionsResponse]
    total: int
    skip: int
    limit: int


class ContributionsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[ContributionsData]


class ContributionsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: ContributionsUpdateData


class ContributionsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[ContributionsBatchUpdateItem]


class ContributionsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=ContributionsListResponse)
async def query_contributionss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query contributionss with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying contributionss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = ContributionsService(db)
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
        logger.debug(f"Found {result['total']} contributionss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying contributionss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=ContributionsListResponse)
async def query_contributionss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query contributionss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying contributionss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = ContributionsService(db)
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
        logger.debug(f"Found {result['total']} contributionss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying contributionss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=ContributionsResponse)
async def get_contributions(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single contributions by ID (user can only see their own records)"""
    logger.debug(f"Fetching contributions with id: {id}, fields={fields}")
    
    service = ContributionsService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Contributions with id {id} not found")
            raise HTTPException(status_code=404, detail="Contributions not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching contributions {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=ContributionsResponse, status_code=201)
async def create_contributions(
    data: ContributionsData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new contributions"""
    logger.debug(f"Creating new contributions with data: {data}")
    
    service = ContributionsService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create contributions")
        
        logger.info(f"Contributions created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating contributions: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating contributions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[ContributionsResponse], status_code=201)
async def create_contributionss_batch(
    request: ContributionsBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple contributionss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} contributionss")
    
    service = ContributionsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} contributionss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[ContributionsResponse])
async def update_contributionss_batch(
    request: ContributionsBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple contributionss in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} contributionss")
    
    service = ContributionsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} contributionss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=ContributionsResponse)
async def update_contributions(
    id: int,
    data: ContributionsUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing contributions (requires ownership)"""
    logger.debug(f"Updating contributions {id} with data: {data}")

    service = ContributionsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Contributions with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Contributions not found")
        
        logger.info(f"Contributions {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating contributions {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating contributions {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_contributionss_batch(
    request: ContributionsBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple contributionss by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} contributionss")
    
    service = ContributionsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} contributionss successfully")
        return {"message": f"Successfully deleted {deleted_count} contributionss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_contributions(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single contributions by ID (requires ownership)"""
    logger.debug(f"Deleting contributions with id: {id}")
    
    service = ContributionsService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Contributions with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Contributions not found")
        
        logger.info(f"Contributions {id} deleted successfully")
        return {"message": "Contributions deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting contributions {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")