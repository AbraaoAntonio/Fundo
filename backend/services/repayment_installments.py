import logging
from typing import Optional, Dict, Any, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.repayment_installments import Repayment_installments

logger = logging.getLogger(__name__)


# ------------------ Service Layer ------------------
class Repayment_installmentsService:
    """Service layer for Repayment_installments operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Repayment_installments]:
        """Create a new repayment_installments"""
        try:
            if user_id:
                data['user_id'] = user_id
            obj = Repayment_installments(**data)
            self.db.add(obj)
            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Created repayment_installments with id: {obj.id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error creating repayment_installments: {str(e)}")
            raise

    async def check_ownership(self, obj_id: int, user_id: str) -> bool:
        """Check if user owns this record"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            return obj is not None
        except Exception as e:
            logger.error(f"Error checking ownership for repayment_installments {obj_id}: {str(e)}")
            return False

    async def get_by_id(self, obj_id: int, user_id: Optional[str] = None) -> Optional[Repayment_installments]:
        """Get repayment_installments by ID (user can only see their own records)"""
        try:
            query = select(Repayment_installments).where(Repayment_installments.id == obj_id)
            if user_id:
                query = query.where(Repayment_installments.user_id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching repayment_installments {obj_id}: {str(e)}")
            raise

    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 20, 
        user_id: Optional[str] = None,
        query_dict: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of repayment_installmentss (user can only see their own records)"""
        try:
            query = select(Repayment_installments)
            count_query = select(func.count(Repayment_installments.id))
            
            if user_id:
                query = query.where(Repayment_installments.user_id == user_id)
                count_query = count_query.where(Repayment_installments.user_id == user_id)
            
            if query_dict:
                for field, value in query_dict.items():
                    if hasattr(Repayment_installments, field):
                        query = query.where(getattr(Repayment_installments, field) == value)
                        count_query = count_query.where(getattr(Repayment_installments, field) == value)
            
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            if sort:
                if sort.startswith('-'):
                    field_name = sort[1:]
                    if hasattr(Repayment_installments, field_name):
                        query = query.order_by(getattr(Repayment_installments, field_name).desc())
                else:
                    if hasattr(Repayment_installments, sort):
                        query = query.order_by(getattr(Repayment_installments, sort))
            else:
                query = query.order_by(Repayment_installments.id.desc())

            result = await self.db.execute(query.offset(skip).limit(limit))
            items = result.scalars().all()

            return {
                "items": items,
                "total": total,
                "skip": skip,
                "limit": limit,
            }
        except Exception as e:
            logger.error(f"Error fetching repayment_installments list: {str(e)}")
            raise

    async def update(self, obj_id: int, update_data: Dict[str, Any], user_id: Optional[str] = None) -> Optional[Repayment_installments]:
        """Update repayment_installments (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            if not obj:
                logger.warning(f"Repayment_installments {obj_id} not found for update")
                return None
            for key, value in update_data.items():
                if hasattr(obj, key) and key != 'user_id':
                    setattr(obj, key, value)

            await self.db.commit()
            await self.db.refresh(obj)
            logger.info(f"Updated repayment_installments {obj_id}")
            return obj
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating repayment_installments {obj_id}: {str(e)}")
            raise

    async def delete(self, obj_id: int, user_id: Optional[str] = None) -> bool:
        """Delete repayment_installments (requires ownership)"""
        try:
            obj = await self.get_by_id(obj_id, user_id=user_id)
            if not obj:
                logger.warning(f"Repayment_installments {obj_id} not found for deletion")
                return False
            await self.db.delete(obj)
            await self.db.commit()
            logger.info(f"Deleted repayment_installments {obj_id}")
            return True
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error deleting repayment_installments {obj_id}: {str(e)}")
            raise

    async def get_by_field(self, field_name: str, field_value: Any) -> Optional[Repayment_installments]:
        """Get repayment_installments by any field"""
        try:
            if not hasattr(Repayment_installments, field_name):
                raise ValueError(f"Field {field_name} does not exist on Repayment_installments")
            result = await self.db.execute(
                select(Repayment_installments).where(getattr(Repayment_installments, field_name) == field_value)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching repayment_installments by {field_name}: {str(e)}")
            raise

    async def list_by_field(
        self, field_name: str, field_value: Any, skip: int = 0, limit: int = 20
    ) -> List[Repayment_installments]:
        """Get list of repayment_installmentss filtered by field"""
        try:
            if not hasattr(Repayment_installments, field_name):
                raise ValueError(f"Field {field_name} does not exist on Repayment_installments")
            result = await self.db.execute(
                select(Repayment_installments)
                .where(getattr(Repayment_installments, field_name) == field_value)
                .offset(skip)
                .limit(limit)
                .order_by(Repayment_installments.id.desc())
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error fetching repayment_installmentss by {field_name}: {str(e)}")
            raise