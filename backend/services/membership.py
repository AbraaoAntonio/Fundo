import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from services.profiles import ProfilesService
from services.contributions import ContributionsService
from services.class_upgrades import Class_upgradesService

logger = logging.getLogger(__name__)


class MembershipService:
    """Service for membership-related business logic"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.profiles_service = ProfilesService(db)
        self.contributions_service = ContributionsService(db)
        self.upgrades_service = Class_upgradesService(db)

    async def get_class_limits(self, class_type: str) -> Dict[str, Any]:
        """Get monthly contribution and limit for a class"""
        class_info = {
            "A": {"monthly": 25.00, "limit": 2000.00},
            "B": {"monthly": 50.00, "limit": 3000.00},
            "C": {"monthly": 75.00, "limit": 5000.00},
            "D": {"monthly": 100.00, "limit": 10000.00},
        }
        return class_info.get(class_type, {"monthly": 0, "limit": 0})

    async def check_eligibility(self, user_id: str) -> Dict[str, Any]:
        """Check if user is eligible to request help"""
        profile_list = await self.profiles_service.get_list(user_id=user_id, limit=1)
        
        if not profile_list["items"]:
            return {
                "eligible": False,
                "reason": "Perfil não encontrado"
            }
        
        profile = profile_list["items"][0]
        
        # Check join fee
        if not profile.join_fee_paid:
            return {
                "eligible": False,
                "reason": "Taxa de adesão não paga"
            }
        
        # Check consecutive months paid
        if (profile.paid_months_count or 0) < 6:
            return {
                "eligible": False,
                "reason": f"Necessário 6 meses pagos consecutivos. Você tem {profile.paid_months_count or 0} meses."
            }
        
        # Check arrears
        if (profile.months_in_arrears or 0) > 2:
            return {
                "eligible": False,
                "reason": "Mais de 2 meses em atraso. Regularize seus pagamentos."
            }
        
        # Check membership status
        if profile.membership_status != "active":
            return {
                "eligible": False,
                "reason": f"Status da conta: {profile.membership_status}"
            }
        
        class_info = await self.get_class_limits(profile.membership_class)
        
        return {
            "eligible": True,
            "class": profile.membership_class,
            "limit": class_info["limit"],
            "paid_months": profile.paid_months_count
        }

    async def request_class_upgrade(self, user_id: str, to_class: str) -> Dict[str, Any]:
        """Request a class upgrade"""
        profile_list = await self.profiles_service.get_list(user_id=user_id, limit=1)
        
        if not profile_list["items"]:
            raise ValueError("Perfil não encontrado")
        
        profile = profile_list["items"][0]
        from_class = profile.membership_class
        
        # Validate upgrade (no downgrades)
        class_order = {"A": 1, "B": 2, "C": 3, "D": 4}
        if class_order.get(to_class, 0) <= class_order.get(from_class, 0):
            raise ValueError("Não é possível fazer downgrade de classe")
        
        # Check for existing pending upgrade
        existing_upgrades = await self.upgrades_service.get_list(
            user_id=user_id,
            query_dict={"status": "pending"}
        )
        
        if existing_upgrades["items"]:
            raise ValueError("Você já tem uma solicitação de upgrade pendente")
        
        # Create upgrade request
        upgrade_data = {
            "user_id": user_id,
            "profile_id": profile.id,
            "from_class": from_class,
            "to_class": to_class,
            "status": "pending",
            "payments_in_new_class": 0,
            "requested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        upgrade = await self.upgrades_service.create(upgrade_data, user_id)
        
        # Update profile class immediately
        await self.profiles_service.update(
            profile.id,
            {
                "membership_class": to_class,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            user_id
        )
        
        return {
            "success": True,
            "message": f"Upgrade de classe {from_class} para {to_class} solicitado. O novo limite estará disponível após 3 pagamentos.",
            "upgrade_id": upgrade.id
        }

    async def process_monthly_payment(self, user_id: str) -> Dict[str, Any]:
        """Process logic after a monthly payment"""
        profile_list = await self.profiles_service.get_list(user_id=user_id, limit=1)
        
        if not profile_list["items"]:
            return {"success": False, "message": "Perfil não encontrado"}
        
        profile = profile_list["items"][0]
        
        # Check for pending upgrades
        pending_upgrades = await self.upgrades_service.get_list(
            user_id=user_id,
            query_dict={"status": "pending"}
        )
        
        if pending_upgrades["items"]:
            upgrade = pending_upgrades["items"][0]
            new_payments = (upgrade.payments_in_new_class or 0) + 1
            
            await self.upgrades_service.update(
                upgrade.id,
                {"payments_in_new_class": new_payments},
                user_id
            )
            
            # Activate upgrade after 3 payments
            if new_payments >= 3:
                await self.upgrades_service.update(
                    upgrade.id,
                    {
                        "status": "active",
                        "activated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    },
                    user_id
                )
                
                return {
                    "success": True,
                    "message": f"Upgrade para classe {upgrade.to_class} ativado! Novo limite disponível.",
                    "upgrade_activated": True
                }
        
        return {
            "success": True,
            "message": "Pagamento processado com sucesso"
        }