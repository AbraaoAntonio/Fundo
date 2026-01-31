import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.repayments import Repayments

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class RepaymentsService:
    """Service layer for Repayments operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Repayments]:
        """Create a new repayments"""
        try:
            if user_id:
                data['user_id'] = user_id
            obj = Repayments(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created repayments with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating repayments: {str(e)}")
            raise

    async def check_ownership(self, obj_id: int, user_id: str) -> bool:
        """Check if user owns this record"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            return obj is not None
        except Exception as e:
            logger.error(f"Error checking ownership for repayments {obj_id}: {str(e)}")
            return False

    async def get_by_id(self, obj_id: int, user_id: Optional[str] = None) -> Optional[Repayments]:
        """Get repayments by ID (user can only see their own records)"""
        try:
            query = select(Repayments).where(Repayments.id == obj_id)
            if user_id:
                query = query.where(Repayments.user_id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching repayments {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        user_id: Optional[str] = None,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of repaymentss (user can only see their own records)"""
        try:
            query = select(Repayments)
            count_query = select(func.count(Repayments.id))
            
            if user_id:
                query = query.where(Repayments.user_id == user_id)
                count_query = count_query.where(Repayments.user_id == user_id)
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Repayments, field):
                        query = query.where(getattr(Repayments, field) == value)
                        count_query = count_query.where(getattr(Repayments, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Repayments, field_name):
                        query = query.order_by(getattr(Repayments, field_name).desc())
                else:
                    if hasattr(Repayments, sort):
                        query = query.order_by(getattr(Repayments, sort))
            else:
                query = query.order_by(Repayments.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching repayments list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Repayments]:
        """Update repayments (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            if not obj:
                logger.warning(f"Repayments {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key) and key != 'user_id':
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated repayments {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating repayments {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int, user_id: Optional[str] = None) -> bool:
        """Delete repayments (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            if not obj:
                logger.warning(f"Repayments {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted repayments {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting repayments {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Repayments]:
        """Get repayments by any field"""
        try:
            if not hasattr(Repayments, field_name):
                raise ValueError(f"Field {field_name} does not exist on Repayments")
            result = await self.db.execute(
                select(Repayments).where(getattr(Repayments, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching repayments by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Repayments]:
        """Get list of repaymentss filtered by field"""
        try:
            if not hasattr(Repayments, field_name):
                raise ValueError(f"Field {field_name} does not exist on Repayments")
            result = await self.db.execute(
                select(Repayments)
                .where(getattr(Repayments, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Repayments.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching repaymentss by {field_name}: {str(e)}")
            raise