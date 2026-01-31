import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.fund_statistics import Fund_statisticsService

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/fund_statistics", tags=["fund_statistics"])


# ---------- Pydantic Schemas ----------
class Fund_statisticsData(BaseModel):
    """Entity data schema (for create/update)"""
    total_collected: float
    total_disbursed: float
    current_balance: float
    active_members: int
    updated_at: str


class Fund_statisticsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    total_collected: Optional[float] = None
    total_disbursed: Optional[float] = None
    current_balance: Optional[float] = None
    active_members: Optional[int] = None
    updated_at: Optional[str] = None


class Fund_statisticsResponse(BaseModel):
    """Entity response schema"""
    id: int
    total_collected: float
    total_disbursed: float
    current_balance: float
    active_members: int
    updated_at: str

    class Config:
        from_attributes = True


class Fund_statisticsListResponse(BaseModel):
    """List response schema"""
    items: List[Fund_statisticsResponse]
    total: int
    skip: int
    limit: int


class Fund_statisticsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[Fund_statisticsData]


class Fund_statisticsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: Fund_statisticsUpdateData


class Fund_statisticsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[Fund_statisticsBatchUpdateItem]


class Fund_statisticsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=Fund_statisticsListResponse)
async def query_fund_statisticss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Query fund_statisticss with filtering, sorting, and pagination"""
    logger.debug(f"Querying fund_statisticss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = Fund_statisticsService(db)
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
        logger.debug(f"Found {result['total']} fund_statisticss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying fund_statisticss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=Fund_statisticsListResponse)
async def query_fund_statisticss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query fund_statisticss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying fund_statisticss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = Fund_statisticsService(db)
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
        logger.debug(f"Found {result['total']} fund_statisticss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying fund_statisticss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=Fund_statisticsResponse)
async def get_fund_statistics(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    """Get a single fund_statistics by ID"""
    logger.debug(f"Fetching fund_statistics with id: {id}, fields={fields}")
    
    service = Fund_statisticsService(db)
    try:
        result = await service.get_by_id(id)
        if not result:
            logger.warning(f"Fund_statistics with id {id} not found")
            raise HTTPException(status_code=404, detail="Fund_statistics not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching fund_statistics {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=Fund_statisticsResponse, status_code=201)
async def create_fund_statistics(
    data: Fund_statisticsData,
    db: AsyncSession = Depends(get_db),
):
    """Create a new fund_statistics"""
    logger.debug(f"Creating new fund_statistics with data: {data}")
    
    service = Fund_statisticsService(db)
    try:
        result = await service.create(data.model_dump())
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create fund_statistics")
        
        logger.info(f"Fund_statistics created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating fund_statistics: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating fund_statistics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[Fund_statisticsResponse], status_code=201)
async def create_fund_statisticss_batch(
    request: Fund_statisticsBatchCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple fund_statisticss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} fund_statisticss")
    
    service = Fund_statisticsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump())
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} fund_statisticss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[Fund_statisticsResponse])
async def update_fund_statisticss_batch(
    request: Fund_statisticsBatchUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update multiple fund_statisticss in a single request"""
    logger.debug(f"Batch updating {len(request.items)} fund_statisticss")
    
    service = Fund_statisticsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict)
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} fund_statisticss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=Fund_statisticsResponse)
async def update_fund_statistics(
    id: int,
    data: Fund_statisticsUpdateData,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing fund_statistics"""
    logger.debug(f"Updating fund_statistics {id} with data: {data}")

    service = Fund_statisticsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict)
        if not result:
            logger.warning(f"Fund_statistics with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Fund_statistics not found")
        
        logger.info(f"Fund_statistics {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating fund_statistics {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating fund_statistics {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_fund_statisticss_batch(
    request: Fund_statisticsBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple fund_statisticss by their IDs"""
    logger.debug(f"Batch deleting {len(request.ids)} fund_statisticss")
    
    service = Fund_statisticsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id)
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} fund_statisticss successfully")
        return {"message": f"Successfully deleted {deleted_count} fund_statisticss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_fund_statistics(
    id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a single fund_statistics by ID"""
    logger.debug(f"Deleting fund_statistics with id: {id}")
    
    service = Fund_statisticsService(db)
    try:
        success = await service.delete(id)
        if not success:
            logger.warning(f"Fund_statistics with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Fund_statistics not found")
        
        logger.info(f"Fund_statistics {id} deleted successfully")
        return {"message": "Fund_statistics deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting fund_statistics {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")