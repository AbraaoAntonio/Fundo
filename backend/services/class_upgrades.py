import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.class_upgrades import Class_upgrades

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Class_upgradesService:
    """Service layer for Class_upgrades operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Class_upgrades]:
        """Create a new class_upgrades"""
        try:
            if user_id:
                data['user_id'] = user_id
            obj = Class_upgrades(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created class_upgrades with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating class_upgrades: {str(e)}")
            raise

    async def check_ownership(self, obj_id: int, user_id: str) -> bool:
        """Check if user owns this record"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            return obj is not None
        except Exception as e:
            logger.error(f"Error checking ownership for class_upgrades {obj_id}: {str(e)}")
            return False

    async def get_by_id(self, obj_id: int, user_id: Optional[str] = None) -> Optional[Class_upgrades]:
        """Get class_upgrades by ID (user can only see their own records)"""
        try:
            query = select(Class_upgrades).where(Class_upgrades.id == obj_id)
            if user_id:
                query = query.where(Class_upgrades.user_id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching class_upgrades {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        user_id: Optional[str] = None,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of class_upgradess (user can only see their own records)"""
        try:
            query = select(Class_upgrades)
            count_query = select(func.count(Class_upgrades.id))
            
            if user_id:
                query = query.where(Class_upgrades.user_id == user_id)
                count_query = count_query.where(Class_upgrades.user_id == user_id)
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Class_upgrades, field):
                        query = query.where(getattr(Class_upgrades, field) == value)
                        count_query = count_query.where(getattr(Class_upgrades, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Class_upgrades, field_name):
                        query = query.order_by(getattr(Class_upgrades, field_name).desc())
                else:
                    if hasattr(Class_upgrades, sort):
                        query = query.order_by(getattr(Class_upgrades, sort))
            else:
                query = query.order_by(Class_upgrades.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching class_upgrades list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Class_upgrades]:
        """Update class_upgrades (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            if not obj:
                logger.warning(f"Class_upgrades {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key) and key != 'user_id':
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated class_upgrades {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating class_upgrades {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int, user_id: Optional[str] = None) -> bool:
        """Delete class_upgrades (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            if not obj:
                logger.warning(f"Class_upgrades {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted class_upgrades {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting class_upgrades {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Class_upgrades]:
        """Get class_upgrades by any field"""
        try:
            if not hasattr(Class_upgrades, field_name):
                raise ValueError(f"Field {field_name} does not exist on Class_upgrades")
            result = await self.db.execute(
                select(Class_upgrades).where(getattr(Class_upgrades, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching class_upgrades by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Class_upgrades]:
        """Get list of class_upgradess filtered by field"""
        try:
            if not hasattr(Class_upgrades, field_name):
                raise ValueError(f"Field {field_name} does not exist on Class_upgrades")
            result = await self.db.execute(
                select(Class_upgrades)
                .where(getattr(Class_upgrades, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Class_upgrades.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching class_upgradess by {field_name}: {str(e)}")
            raise