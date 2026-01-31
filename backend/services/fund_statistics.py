import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.fund_statistics import Fund_statistics

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Fund_statisticsService:
    """Service layer for Fund_statistics operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any]) -> Optional[Fund_statistics]:
        """Create a new fund_statistics"""
        try:
            obj = Fund_statistics(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created fund_statistics with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating fund_statistics: {str(e)}")
            raise

    async def get_by_id(self, obj_id: int) -> Optional[Fund_statistics]:
        """Get fund_statistics by ID"""
        try:
            query = select(Fund_statistics).where(Fund_statistics.id == obj_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching fund_statistics {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of fund_statisticss"""
        try:
            query = select(Fund_statistics)
            count_query = select(func.count(Fund_statistics.id))
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Fund_statistics, field):
                        query = query.where(getattr(Fund_statistics, field) == value)
                        count_query = count_query.where(getattr(Fund_statistics, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Fund_statistics, field_name):
                        query = query.order_by(getattr(Fund_statistics, field_name).desc())
                else:
                    if hasattr(Fund_statistics, sort):
                        query = query.order_by(getattr(Fund_statistics, sort))
            else:
                query = query.order_by(Fund_statistics.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching fund_statistics list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any]) -> Optional[Fund_statistics]:
        """Update fund_statistics"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Fund_statistics {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated fund_statistics {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating fund_statistics {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int) -> bool:
        """Delete fund_statistics"""
        try:
            obj = await self.get_by_id(obj_id)
            if not obj:
                logger.warning(f"Fund_statistics {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted fund_statistics {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting fund_statistics {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Fund_statistics]:
        """Get fund_statistics by any field"""
        try:
            if not hasattr(Fund_statistics, field_name):
                raise ValueError(f"Field {field_name} does not exist on Fund_statistics")
            result = await self.db.execute(
                select(Fund_statistics).where(getattr(Fund_statistics, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching fund_statistics by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Fund_statistics]:
        """Get list of fund_statisticss filtered by field"""
        try:
            if not hasattr(Fund_statistics, field_name):
                raise ValueError(f"Field {field_name} does not exist on Fund_statistics")
            result = await self.db.execute(
                select(Fund_statistics)
                .where(getattr(Fund_statistics, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Fund_statistics.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching fund_statisticss by {field_name}: {str(e)}")
            raise