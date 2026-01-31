import json
import logging
from typing import List, Optional


from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.documents import DocumentsService
from dependencies.auth import get_current_user
from schemas.auth import UserResponse

# Set up logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/entities/documents", tags=["documents"])


# ---------- Pydantic Schemas ----------
class DocumentsData(BaseModel):
    """Entity data schema (for create/update)"""
    request_id: int = None
    document_type: str = None
    file_name: str = None
    file_url: str = None
    uploaded_at: str = None


class DocumentsUpdateData(BaseModel):
    """Update entity data (partial updates allowed)"""
    request_id: Optional[int] = None
    document_type: Optional[str] = None
    file_name: Optional[str] = None
    file_url: Optional[str] = None
    uploaded_at: Optional[str] = None


class DocumentsResponse(BaseModel):
    """Entity response schema"""
    id: int
    user_id: str
    request_id: Optional[int] = None
    document_type: Optional[str] = None
    file_name: Optional[str] = None
    file_url: Optional[str] = None
    uploaded_at: Optional[str] = None

    class Config:
        from_attributes = True


class DocumentsListResponse(BaseModel):
    """List response schema"""
    items: List[DocumentsResponse]
    total: int
    skip: int
    limit: int


class DocumentsBatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[DocumentsData]


class DocumentsBatchUpdateItem(BaseModel):
    """Batch update item"""
    id: int
    updates: DocumentsUpdateData


class DocumentsBatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[DocumentsBatchUpdateItem]


class DocumentsBatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[int]


# ---------- Routes ----------
@router.get("", response_model=DocumentsListResponse)
async def query_documentss(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Query documentss with filtering, sorting, and pagination (user can only see their own records)"""
    logger.debug(f"Querying documentss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")
    
    service = DocumentsService(db)
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
        logger.debug(f"Found {result['total']} documentss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying documentss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/all", response_model=DocumentsListResponse)
async def query_documentss_all(
    query: str = Query(None, description="Query conditions (JSON string)"),
    sort: str = Query(None, description="Sort field (prefix with '-' for descending)"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=2000, description="Max number of records to return"),
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    db: AsyncSession = Depends(get_db),
):
    # Query documentss with filtering, sorting, and pagination without user limitation
    logger.debug(f"Querying documentss: query={query}, sort={sort}, skip={skip}, limit={limit}, fields={fields}")

    service = DocumentsService(db)
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
        logger.debug(f"Found {result['total']} documentss")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying documentss: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/{id}", response_model=DocumentsResponse)
async def get_documents(
    id: int,
    fields: str = Query(None, description="Comma-separated list of fields to return"),
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single documents by ID (user can only see their own records)"""
    logger.debug(f"Fetching documents with id: {id}, fields={fields}")
    
    service = DocumentsService(db)
    try:
        result = await service.get_by_id(id, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Documents with id {id} not found")
            raise HTTPException(status_code=404, detail="Documents not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching documents {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("", response_model=DocumentsResponse, status_code=201)
async def create_documents(
    data: DocumentsData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new documents"""
    logger.debug(f"Creating new documents with data: {data}")
    
    service = DocumentsService(db)
    try:
        result = await service.create(data.model_dump(), user_id=str(current_user.id))
        if not result:
            raise HTTPException(status_code=400, detail="Failed to create documents")
        
        logger.info(f"Documents created successfully with id: {result.id}")
        return result
    except ValueError as e:
        logger.error(f"Validation error creating documents: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating documents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/batch", response_model=List[DocumentsResponse], status_code=201)
async def create_documentss_batch(
    request: DocumentsBatchCreateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple documentss in a single request"""
    logger.debug(f"Batch creating {len(request.items)} documentss")
    
    service = DocumentsService(db)
    results = []
    
    try:
        for item_data in request.items:
            result = await service.create(item_data.model_dump(), user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch created {len(results)} documentss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch create: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch create failed: {str(e)}")


@router.put("/batch", response_model=List[DocumentsResponse])
async def update_documentss_batch(
    request: DocumentsBatchUpdateRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update multiple documentss in a single request (requires ownership)"""
    logger.debug(f"Batch updating {len(request.items)} documentss")
    
    service = DocumentsService(db)
    results = []
    
    try:
        for item in request.items:
            # Only include non-None values for partial updates
            update_dict = {k: v for k, v in item.updates.model_dump().items() if v is not None}
            result = await service.update(item.id, update_dict, user_id=str(current_user.id))
            if result:
                results.append(result)
        
        logger.info(f"Batch updated {len(results)} documentss successfully")
        return results
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch update: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch update failed: {str(e)}")


@router.put("/{id}", response_model=DocumentsResponse)
async def update_documents(
    id: int,
    data: DocumentsUpdateData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing documents (requires ownership)"""
    logger.debug(f"Updating documents {id} with data: {data}")

    service = DocumentsService(db)
    try:
        # Only include non-None values for partial updates
        update_dict = {k: v for k, v in data.model_dump().items() if v is not None}
        result = await service.update(id, update_dict, user_id=str(current_user.id))
        if not result:
            logger.warning(f"Documents with id {id} not found for update")
            raise HTTPException(status_code=404, detail="Documents not found")
        
        logger.info(f"Documents {id} updated successfully")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error updating documents {id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating documents {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.delete("/batch")
async def delete_documentss_batch(
    request: DocumentsBatchDeleteRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple documentss by their IDs (requires ownership)"""
    logger.debug(f"Batch deleting {len(request.ids)} documentss")
    
    service = DocumentsService(db)
    deleted_count = 0
    
    try:
        for item_id in request.ids:
            success = await service.delete(item_id, user_id=str(current_user.id))
            if success:
                deleted_count += 1
        
        logger.info(f"Batch deleted {deleted_count} documentss successfully")
        return {"message": f"Successfully deleted {deleted_count} documentss", "deleted_count": deleted_count}
    except Exception as e:
        await db.rollback()
        logger.error(f"Error in batch delete: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Batch delete failed: {str(e)}")


@router.delete("/{id}")
async def delete_documents(
    id: int,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a single documents by ID (requires ownership)"""
    logger.debug(f"Deleting documents with id: {id}")
    
    service = DocumentsService(db)
    try:
        success = await service.delete(id, user_id=str(current_user.id))
        if not success:
            logger.warning(f"Documents with id {id} not found for deletion")
            raise HTTPException(status_code=404, detail="Documents not found")
        
        logger.info(f"Documents {id} deleted successfully")
        return {"message": "Documents deleted successfully", "id": id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting documents {id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")