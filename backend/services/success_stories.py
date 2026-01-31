import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.success_stories import Success_stories

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Success_storiesService:
    """Service layer for Success_stories operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Success_stories]:
        """Create a new success_stories"""
        try:
            obj = Success_stories(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created success_stories with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating success_stories: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Success_stories]:
        """Get success_stories by ID"""
        try:
            query = select(Success_stories).where(Success_stories.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching success_stories {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of success_storiess"""
        try:
            query = select(Success_stories)
            count_query = select(func.count(Success_stories.id))
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Success_stories, field):
                        query = query.where(getattr(Success_stories, field) == value)
                        count_query = count_query.where(getattr(Success_stories, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Success_stories, field_name):
                        query = query.order_by(getattr(Success_stories, field_name).desc())
                else:
                    if hasattr(Success_stories, sort):
                        query = query.order_by(getattr(Success_stories, sort))
            else:
                query = query.order_by(Success_stories.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching success_stories list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any]) -> Optional[Success_stories]:
        """Update success_stories"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Success_stories {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated success_stories {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating success_stories {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete success_stories"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Success_stories {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted success_stories {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting success_stories {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Success_stories]:
        """Get success_stories by any field"""
        try:
            if not hasattr(Success_stories, field_name):
                raise ValueError(f"Field {field_name} does not exist on Success_stories")
            result = await self.db.execute(
                select(Success_stories).where(getattr(Success_stories, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching success_stories by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Success_stories]:
        """Get list of success_storiess filtered by field"""
        try:
            if not hasattr(Success_stories, field_name):
                raise ValueError(f"Field {field_name} does not exist on Success_stories")
            result = await self.db.execute(
                select(Success_stories)
                .where(getattr(Success_stories, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Success_stories.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching success_storiess by {field_name}: {str(e)}")
            raise