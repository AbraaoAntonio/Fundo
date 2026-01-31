import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from datetime import datetime
from typing import Optional

from core.database import get_db
from dependencies.auth import get_current_user
from schemas.auth import UserResponse
from models.admins import Admins
from models.profiles import Profiles
from models.requests import Requests
from models.contributions import Contributions
from models.repayments import Repayments
from models.fund_statistics import Fund_statistics

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

logger = logging.getLogger(__name__)

async def verify_admin(current_user: UserResponse, db: AsyncSession):
    """Verify if current user is an admin"""
    result = await db.execute(
        select(Admins).where(Admins.user_id == current_user.id)
    )
    admin = result.scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=403, detail="Access denied. Admin privileges required.")
    return admin

class ApproveRequestData(BaseModel):
    request_id: int
    approved_amount: float
    admin_notes: Optional[str] = None

class RejectRequestData(BaseModel):
    request_id: int
    admin_notes: str

class UpdateStatisticsData(BaseModel):
    total_disbursed: float

@router.get("/verify")
async def verify_admin_access(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify if user has admin access"""
    try:
        admin = await verify_admin(current_user, db)
        return {
            "is_admin": True,
            "admin_id": admin.id,
            "role": admin.role,
            "full_name": admin.full_name
        }
    except HTTPException:
        return {"is_admin": False}

@router.get("/dashboard/statistics")
async def get_admin_statistics(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive statistics for admin dashboard"""
    await verify_admin(current_user, db)
    
    # Count active members
    active_members_result = await db.execute(
        select(func.count(Profiles.id)).where(Profiles.account_status == "active")
    )
    active_members = active_members_result.scalar() or 0
    
    # Count pending requests
    pending_requests_result = await db.execute(
        select(func.count(Requests.id)).where(Requests.status == "pending")
    )
    pending_requests = pending_requests_result.scalar() or 0
    
    # Sum total contributions
    total_contributions_result = await db.execute(
        select(func.sum(Contributions.amount))
    )
    total_contributions = total_contributions_result.scalar() or 0
    
    # Sum approved amounts
    approved_amount_result = await db.execute(
        select(func.sum(Requests.approved_amount)).where(Requests.status == "approved")
    )
    total_disbursed = approved_amount_result.scalar() or 0
    
    # Count members with payment issues
    late_members_result = await db.execute(
        select(func.count(Profiles.id)).where(Profiles.months_late > 0)
    )
    late_members = late_members_result.scalar() or 0
    
    current_balance = total_contributions - total_disbursed
    
    return {
        "active_members": active_members,
        "pending_requests": pending_requests,
        "total_collected": round(total_contributions, 2),
        "total_disbursed": round(total_disbursed, 2),
        "current_balance": round(current_balance, 2),
        "late_members": late_members
    }

@router.get("/members")
async def get_all_members(
    skip: int = 0,
    limit: int = 50,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all members with their details"""
    await verify_admin(current_user, db)
    
    result = await db.execute(
        select(Profiles)
        .order_by(Profiles.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    members = result.scalars().all()
    
    # Get contribution count for each member
    members_data = []
    for member in members:
        contributions_result = await db.execute(
            select(func.count(Contributions.id), func.sum(Contributions.amount))
            .where(Contributions.profile_id == member.id)
        )
        contrib_count, contrib_total = contributions_result.first()
        
        members_data.append({
            "id": member.id,
            "user_id": member.user_id,
            "full_name": member.full_name,
            "phone": member.phone,
            "membership_class": member.membership_class,
            "account_status": member.account_status,
            "consecutive_months_paid": member.consecutive_months_paid,
            "months_late": member.months_late,
            "total_contributions": round(contrib_total or 0, 2),
            "contribution_count": contrib_count or 0,
            "created_at": member.created_at.isoformat() if hasattr(member.created_at, 'isoformat') else str(member.created_at)
        })
    
    return {"members": members_data}

@router.get("/requests/pending")
async def get_pending_requests(
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all pending requests for approval"""
    await verify_admin(current_user, db)
    
    result = await db.execute(
        select(Requests)
        .where(Requests.status == "pending")
        .order_by(Requests.created_at.desc())
    )
    requests = result.scalars().all()
    
    requests_data = []
    for req in requests:
        # Get member info
        member_result = await db.execute(
            select(Profiles).where(Profiles.id == req.profile_id)
        )
        member = member_result.scalar_one_or_none()
        
        requests_data.append({
            "id": req.id,
            "profile_id": req.profile_id,
            "member_name": member.full_name if member else "Unknown",
            "membership_class": member.membership_class if member else "Unknown",
            "request_type": req.request_type,
            "requested_amount": req.requested_amount,
            "payout_type": req.payout_type,
            "payout_recipient_name": req.payout_recipient_name,
            "description": req.description,
            "created_at": req.created_at.isoformat() if hasattr(req.created_at, 'isoformat') else str(req.created_at)
        })
    
    return {"requests": requests_data}

@router.post("/requests/approve")
async def approve_request(
    data: ApproveRequestData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve a request and set approved amount"""
    admin = await verify_admin(current_user, db)
    
    # Get request
    result = await db.execute(
        select(Requests).where(Requests.id == data.request_id)
    )
    request = result.scalar_one_or_none()
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.status != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")
    
    # Update request
    await db.execute(
        update(Requests)
        .where(Requests.id == data.request_id)
        .values(
            status="approved",
            approved_amount=data.approved_amount,
            admin_notes=data.admin_notes,
            approved_by=admin.id,
            approved_at=datetime.now()
        )
    )
    
    # Create repayment plan
    total_to_repay = data.approved_amount * 1.02  # 2% admin fee
    installment_amount = total_to_repay / 12
    
    from models.repayments import Repayments
    repayment = Repayments(
        profile_id=request.profile_id,
        request_id=data.request_id,
        total_to_repay=total_to_repay,
        installment_amount=installment_amount,
        installments=12,
        paid_installments=0,
        status="active",
        next_due_date=datetime.now(),
        created_at=datetime.now()
    )
    db.add(repayment)
    await db.flush()
    
    # Create installments
    from models.repayment_installments import RepaymentInstallments
    from datetime import timedelta
    
    for i in range(1, 13):
        due_date = datetime.now() + timedelta(days=30 * i)
        installment = RepaymentInstallments(
            repayment_id=repayment.id,
            installment_number=i,
            amount=installment_amount,
            due_date=due_date,
            status="pending"
        )
        db.add(installment)
    
    await db.commit()
    
    return {"message": "Request approved successfully", "repayment_id": repayment.id}

@router.post("/requests/reject")
async def reject_request(
    data: RejectRequestData,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reject a request"""
    admin = await verify_admin(current_user, db)
    
    result = await db.execute(
        select(Requests).where(Requests.id == data.request_id)
    )
    request = result.scalar_one_or_none()
    
    if not request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    if request.status != "pending":
        raise HTTPException(status_code=400, detail="Request is not pending")
    
    await db.execute(
        update(Requests)
        .where(Requests.id == data.request_id)
        .values(
            status="rejected",
            admin_notes=data.admin_notes,
            approved_by=admin.id,
            approved_at=datetime.now()
        )
    )
    
    await db.commit()
    
    return {"message": "Request rejected successfully"}

@router.get("/payments/history")
async def get_payment_history(
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all payment history"""
    await verify_admin(current_user, db)
    
    result = await db.execute(
        select(Contributions)
        .order_by(Contributions.payment_date.desc())
        .offset(skip)
        .limit(limit)
    )
    contributions = result.scalars().all()
    
    payments_data = []
    for contrib in contributions:
        member_result = await db.execute(
            select(Profiles).where(Profiles.id == contrib.profile_id)
        )
        member = member_result.scalar_one_or_none()
        
        payments_data.append({
            "id": contrib.id,
            "member_name": member.full_name if member else "Unknown",
            "payment_type": contrib.payment_type,
            "amount": contrib.amount,
            "payment_date": contrib.payment_date.isoformat() if hasattr(contrib.payment_date, 'isoformat') else str(contrib.payment_date)
        })
    
    return {"payments": payments_data}