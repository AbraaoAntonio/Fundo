import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.database import get_db
from models.profiles import Profiles
from models.requests import Requests
from models.contributions import Contributions
from models.success_stories import Success_stories

router = APIRouter(prefix="/api/v1/public", tags=["public"])

logger = logging.getLogger(__name__)

@router.get("/statistics")
async def get_public_statistics(db: AsyncSession = Depends(get_db)):
    """Get public fund statistics visible to all users"""
    
    # Count active members
    active_members_result = await db.execute(
        select(func.count(Profiles.id)).where(Profiles.account_status == "active")
    )
    active_members = active_members_result.scalar() or 0
    
    # Sum total contributions
    total_contributions_result = await db.execute(
        select(func.sum(Contributions.amount))
    )
    total_collected = total_contributions_result.scalar() or 0
    
    # Sum approved amounts (disbursed)
    approved_amount_result = await db.execute(
        select(func.sum(Requests.approved_amount)).where(Requests.status == "approved")
    )
    total_disbursed = approved_amount_result.scalar() or 0
    
    # Count requests by status
    pending_count_result = await db.execute(
        select(func.count(Requests.id)).where(Requests.status == "pending")
    )
    pending_count = pending_count_result.scalar() or 0
    
    approved_count_result = await db.execute(
        select(func.count(Requests.id)).where(Requests.status == "approved")
    )
    approved_count = approved_count_result.scalar() or 0
    
    rejected_count_result = await db.execute(
        select(func.count(Requests.id)).where(Requests.status == "rejected")
    )
    rejected_count = rejected_count_result.scalar() or 0
    
    return {
        "total_collected": round(total_collected, 2),
        "total_disbursed": round(total_disbursed, 2),
        "current_balance": round(total_collected - total_disbursed, 2),
        "active_members": active_members,
        "requests": {
            "pending": pending_count,
            "approved": approved_count,
            "rejected": rejected_count
        }
    }

@router.get("/success-stories")
async def get_success_stories(
    limit: int = 10,
    db: AsyncSession = Depends(get_db)
):
    """Get published success stories"""
    
    result = await db.execute(
        select(Success_stories)
        .where(Success_stories.is_published == True)
        .order_by(Success_stories.created_at.desc())
        .limit(limit)
    )
    stories = result.scalars().all()
    
    stories_data = []
    for story in stories:
        stories_data.append({
            "id": story.id,
            "member_name": story.member_name,
            "story": story.story,
            "amount_received": story.amount_received,
            "created_at": story.created_at.isoformat() if hasattr(story.created_at, 'isoformat') else str(story.created_at)
        })
    
    return {"stories": stories_data}