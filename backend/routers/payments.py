import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime, timedelta
import stripe
import os

from core.database import get_db
from dependencies.auth import get_current_user
from schemas.auth import UserResponse
from models.profiles import Profiles
from models.contributions import Contributions
from models.repayment_installments import RepaymentInstallments

stripe_key = os.environ.get("STRIPE_SECRET_KEY")
if not stripe_key:
    raise ValueError("STRIPE_SECRET_KEY environment variable is not set")
stripe.api_key = stripe_key

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])

class CheckoutSessionRequest(BaseModel):
    payment_type: str
    installment_id: int = None

class CheckoutSessionResponse(BaseModel):
    session_id: str
    url: str

class PaymentVerificationRequest(BaseModel):
    session_id: str

class PaymentStatusResponse(BaseModel):
    status: str
    order_id: int = None
    payment_status: str = None

@router.post("/create_payment_session", response_model=CheckoutSessionResponse)
async def create_payment_session(
    data: CheckoutSessionRequest,
    request: Request,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe checkout session or subscription"""
    try:
        frontend_host = request.headers.get("App-Host")
        if frontend_host and not frontend_host.startswith(("http://", "https://")):
            frontend_host = f"https://{frontend_host}"

        # Get user profile
        result = await db.execute(
            select(Profiles).where(Profiles.user_id == current_user.id)
        )
        profile = result.scalar_one_or_none()
        
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        # Join fee - one-time payment
        if data.payment_type == "join_fee":
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "Membership Fee",
                            "description": "One-time membership activation fee"
                        },
                        "unit_amount": 10000,  # $100.00
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=f"{frontend_host}/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{frontend_host}/payments/join-fee",
                metadata={
                    "payment_type": "join_fee",
                    "user_id": current_user.id,
                    "profile_id": str(profile.id)
                }
            )
            
            return CheckoutSessionResponse(
                session_id=session.id,
                url=session.url
            )

        # Monthly subscription - recurring payment
        elif data.payment_type == "monthly":
            # Get monthly amount based on class
            class_amounts = {"A": 2500, "B": 5000, "C": 7500, "D": 10000}  # in cents
            amount = class_amounts.get(profile.membership_class, 2500)
            
            # Create or retrieve customer
            customers = stripe.Customer.list(email=current_user.email, limit=1)
            if customers.data:
                customer = customers.data[0]
            else:
                customer = stripe.Customer.create(
                    email=current_user.email,
                    name=profile.full_name,
                    metadata={
                        "user_id": current_user.id,
                        "profile_id": str(profile.id)
                    }
                )
            
            # Create subscription checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"Class {profile.membership_class} Monthly Contribution",
                            "description": f"Recurring monthly payment for Class {profile.membership_class}"
                        },
                        "unit_amount": amount,
                        "recurring": {
                            "interval": "month",
                            "interval_count": 1
                        }
                    },
                    "quantity": 1,
                }],
                mode="subscription",
                customer=customer.id,
                success_url=f"{frontend_host}/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{frontend_host}/payments/monthly",
                metadata={
                    "payment_type": "monthly",
                    "user_id": current_user.id,
                    "profile_id": str(profile.id),
                    "membership_class": profile.membership_class
                },
                subscription_data={
                    "metadata": {
                        "user_id": current_user.id,
                        "profile_id": str(profile.id),
                        "membership_class": profile.membership_class
                    }
                }
            )
            
            return CheckoutSessionResponse(
                session_id=session.id,
                url=session.url
            )

        # Installment payment
        elif data.payment_type == "installment":
            if not data.installment_id:
                raise HTTPException(status_code=400, detail="installment_id is required")
            
            result = await db.execute(
                select(RepaymentInstallments).where(RepaymentInstallments.id == data.installment_id)
            )
            installment = result.scalar_one_or_none()
            
            if not installment:
                raise HTTPException(status_code=404, detail="Installment not found")
            
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"Repayment Installment #{installment.installment_number}",
                            "description": f"Installment payment for repayment plan"
                        },
                        "unit_amount": int(installment.amount * 100),
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=f"{frontend_host}/payment-success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{frontend_host}/repayments",
                metadata={
                    "payment_type": "installment",
                    "user_id": current_user.id,
                    "installment_id": str(installment.id)
                }
            )
            
            return CheckoutSessionResponse(
                session_id=session.id,
                url=session.url
            )

        else:
            raise HTTPException(status_code=400, detail="Invalid payment type")

    except stripe.error.StripeError as e:
        logging.error(f"Stripe error: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        logging.error(f"Payment session creation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create payment session: {str(e)}")

@router.post("/verify_payment", response_model=PaymentStatusResponse)
async def verify_payment(
    data: PaymentVerificationRequest,
    current_user: UserResponse = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify payment status and update records"""
    try:
        session = stripe.checkout.Session.retrieve(data.session_id)
        payment_type = session.metadata.get("payment_type")
        
        if session.payment_status == "paid":
            # Get profile
            result = await db.execute(
                select(Profiles).where(Profiles.user_id == current_user.id)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                raise HTTPException(status_code=404, detail="Profile not found")
            
            # Handle join fee payment
            if payment_type == "join_fee":
                await db.execute(
                    update(Profiles)
                    .where(Profiles.id == profile.id)
                    .values(
                        account_status="active",
                        updated_at=datetime.now()
                    )
                )
                
                # Record contribution
                contribution = Contributions(
                    profile_id=profile.id,
                    payment_type="join_fee",
                    amount=100.00,
                    payment_date=datetime.now(),
                    stripe_payment_id=session.payment_intent
                )
                db.add(contribution)
            
            # Handle monthly subscription payment
            elif payment_type == "monthly":
                # Update consecutive months
                new_consecutive = profile.consecutive_months_paid + 1
                await db.execute(
                    update(Profiles)
                    .where(Profiles.id == profile.id)
                    .values(
                        consecutive_months_paid=new_consecutive,
                        months_late=0,
                        stripe_subscription_id=session.subscription,
                        updated_at=datetime.now()
                    )
                )
                
                # Record contribution
                class_amounts = {"A": 25, "B": 50, "C": 75, "D": 100}
                amount = class_amounts.get(profile.membership_class, 25)
                
                contribution = Contributions(
                    profile_id=profile.id,
                    payment_type="monthly",
                    amount=amount,
                    payment_date=datetime.now(),
                    stripe_payment_id=session.payment_intent
                )
                db.add(contribution)
            
            # Handle installment payment
            elif payment_type == "installment":
                installment_id = int(session.metadata.get("installment_id"))
                await db.execute(
                    update(RepaymentInstallments)
                    .where(RepaymentInstallments.id == installment_id)
                    .values(
                        status="paid",
                        paid_date=datetime.now(),
                        stripe_payment_id=session.payment_intent
                    )
                )
            
            await db.commit()
        
        return PaymentStatusResponse(
            status="paid" if session.payment_status == "paid" else "pending",
            payment_status=session.payment_status
        )
        
    except stripe.error.StripeError as e:
        logging.error(f"Stripe verification error: {e}")
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")
    except Exception as e:
        logging.error(f"Payment verification error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to verify payment: {str(e)}")

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Stripe webhook events for subscription renewals"""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        # In production, use webhook secret: stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        event = stripe.Event.construct_from(
            stripe.util.convert_to_dict(payload), stripe.api_key
        )
        
        # Handle subscription invoice paid (monthly recurring payment)
        if event.type == "invoice.paid":
            invoice = event.data.object
            subscription_id = invoice.subscription
            
            if subscription_id:
                # Get subscription metadata
                subscription = stripe.Subscription.retrieve(subscription_id)
                profile_id = subscription.metadata.get("profile_id")
                
                if profile_id:
                    # Get profile
                    result = await db.execute(
                        select(Profiles).where(Profiles.id == int(profile_id))
                    )
                    profile = result.scalar_one_or_none()
                    
                    if profile:
                        # Update consecutive months
                        new_consecutive = profile.consecutive_months_paid + 1
                        await db.execute(
                            update(Profiles)
                            .where(Profiles.id == profile.id)
                            .values(
                                consecutive_months_paid=new_consecutive,
                                months_late=0,
                                updated_at=datetime.now()
                            )
                        )
                        
                        # Record contribution
                        class_amounts = {"A": 25, "B": 50, "C": 75, "D": 100}
                        amount = class_amounts.get(profile.membership_class, 25)
                        
                        contribution = Contributions(
                            profile_id=profile.id,
                            payment_type="monthly",
                            amount=amount,
                            payment_date=datetime.now(),
                            stripe_payment_id=invoice.payment_intent
                        )
                        db.add(contribution)
                        await db.commit()
        
        # Handle subscription payment failed
        elif event.type == "invoice.payment_failed":
            invoice = event.data.object
            subscription_id = invoice.subscription
            
            if subscription_id:
                subscription = stripe.Subscription.retrieve(subscription_id)
                profile_id = subscription.metadata.get("profile_id")
                
                if profile_id:
                    # Increment months late
                    result = await db.execute(
                        select(Profiles).where(Profiles.id == int(profile_id))
                    )
                    profile = result.scalar_one_or_none()
                    
                    if profile:
                        new_late = profile.months_late + 1
                        new_status = "paused" if new_late >= 3 else profile.account_status
                        new_consecutive = 0 if new_late >= 3 else profile.consecutive_months_paid
                        
                        await db.execute(
                            update(Profiles)
                            .where(Profiles.id == profile.id)
                            .values(
                                months_late=new_late,
                                account_status=new_status,
                                consecutive_months_paid=new_consecutive,
                                updated_at=datetime.now()
                            )
                        )
                        await db.commit()
        
        return {"status": "success"}
        
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        raise HTTPException(status_code=400, detail=str(e))