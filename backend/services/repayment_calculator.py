import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

logger = logging.getLogger(__name__)


class RepaymentCalculator:
    """Service for calculating repayment plans"""

    @staticmethod
    def calculate_repayment_plan(
        approved_amount: float,
        installments: int = 12
    ) -> Dict[str, Any]:
        """
        Calculate repayment plan with 2% administrative fee
        
        Args:
            approved_amount: The approved loan amount
            installments: Number of installments (max 12)
        
        Returns:
            Dict with total_to_repay, installment_amount, and installment_schedule
        """
        if installments < 1 or installments > 12:
            raise ValueError("Installments must be between 1 and 12")
        
        # Calculate total with 2% administrative fee
        total_to_repay = approved_amount * 1.02
        installment_amount = total_to_repay / installments
        
        # Generate installment schedule
        schedule = []
        current_date = datetime.now()
        
        for i in range(1, installments + 1):
            due_date = current_date + relativedelta(months=i)
            schedule.append({
                "installment_number": i,
                "amount": round(installment_amount, 2),
                "due_date": due_date.strftime("%Y-%m-%d"),
                "status": "pending"
            })
        
        return {
            "approved_amount": approved_amount,
            "administrative_fee": approved_amount * 0.02,
            "total_to_repay": round(total_to_repay, 2),
            "installments": installments,
            "installment_amount": round(installment_amount, 2),
            "schedule": schedule,
            "first_due_date": schedule[0]["due_date"],
            "last_due_date": schedule[-1]["due_date"]
        }

    @staticmethod
    def check_overdue_installments(installments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Check for overdue installments
        
        Args:
            installments: List of installment records
        
        Returns:
            Dict with overdue count and details
        """
        today = datetime.now().date()
        overdue = []
        
        for inst in installments:
            if inst.get("status") == "pending":
                due_date = datetime.strptime(inst.get("due_date"), "%Y-%m-%d").date()
                if due_date < today:
                    days_overdue = (today - due_date).days
                    overdue.append({
                        "installment_number": inst.get("installment_number"),
                        "amount": inst.get("amount"),
                        "due_date": inst.get("due_date"),
                        "days_overdue": days_overdue
                    })
        
        return {
            "has_overdue": len(overdue) > 0,
            "overdue_count": len(overdue),
            "overdue_installments": overdue,
            "total_overdue_amount": sum(inst["amount"] for inst in overdue)
        }