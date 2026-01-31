from core.database import Base
from sqlalchemy import Column, Integer, String


class Profiles(Base):
    __tablename__ = "profiles"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    user_id = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    membership_class = Column(String, nullable=False)
    account_status = Column(String, nullable=False)
    consecutive_months_paid = Column(Integer, nullable=True)
    months_late = Column(Integer, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    created_at = Column(String, nullable=False)
    updated_at = Column(String, nullable=False)