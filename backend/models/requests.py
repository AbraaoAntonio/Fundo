from core.database import Base
from sqlalchemy import Column, Float, Integer, String


class Requests(Base):
    __tablename__ = "requests"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    user_id = Column(String, nullable=False)
    profile_id = Column(Integer, nullable=True)
    request_type = Column(String, nullable=True)
    requested_amount = Column(Float, nullable=True)
    approved_amount = Column(Float, nullable=True)
    status = Column(String, nullable=True)
    payout_type = Column(String, nullable=True)
    payout_recipient_name = Column(String, nullable=True)
    payout_recipient_account = Column(String, nullable=True)
    description = Column(String, nullable=True)
    admin_notes = Column(String, nullable=True)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)