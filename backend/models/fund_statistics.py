from core.database import Base
from sqlalchemy import Column, Float, Integer, String


class Fund_statistics(Base):
    __tablename__ = "fund_statistics"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    total_collected = Column(Float, nullable=False)
    total_disbursed = Column(Float, nullable=False)
    current_balance = Column(Float, nullable=False)
    active_members = Column(Integer, nullable=False)
    updated_at = Column(String, nullable=False)