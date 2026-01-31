from core.database import Base
from sqlalchemy import Column, Float, Integer, String


class Repayments(Base):
    __tablename__ = "repayments"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    user_id = Column(String, nullable=False)
    request_id = Column(Integer, nullable=True)
    total_to_repay = Column(Float, nullable=True)
    installments = Column(Integer, nullable=True)
    installment_amount = Column(Float, nullable=True)
    paid_installments = Column(Integer, nullable=True)
    status = Column(String, nullable=True)
    next_due_date = Column(String, nullable=True)
    created_at = Column(String, nullable=True)
    updated_at = Column(String, nullable=True)