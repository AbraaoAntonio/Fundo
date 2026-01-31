from core.database import Base
from sqlalchemy import Column, Float, Integer, String


class Contributions(Base):
    __tablename__ = "contributions"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    user_id = Column(String, nullable=False)
    profile_id = Column(Integer, nullable=True)
    contribution_type = Column(String, nullable=True)
    amount = Column(Float, nullable=True)
    status = Column(String, nullable=True)
    payment_date = Column(String, nullable=True)
    stripe_payment_id = Column(String, nullable=True)
    created_at = Column(String, nullable=True)