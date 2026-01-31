from core.database import Base
from sqlalchemy import Column, Float, Integer, String


class Payouts(Base):
    __tablename__ = "payouts"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    user_id = Column(String, nullable=False)
    request_id = Column(Integer, nullable=True)
    amount = Column(Float, nullable=True)
    recipient_type = Column(String, nullable=True)
    recipient_name = Column(String, nullable=True)
    recipient_account = Column(String, nullable=True)
    status = Column(String, nullable=True)
    stripe_payout_id = Column(String, nullable=True)
    processed_at = Column(String, nullable=True)
    created_at = Column(String, nullable=True)