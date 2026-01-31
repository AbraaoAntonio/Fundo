from core.database import Base
from sqlalchemy import Column, Float, Integer, String


class Repayment_installments(Base):
    __tablename__ = "repayment_installments"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    user_id = Column(String, nullable=False)
    repayment_id = Column(Integer, nullable=True)
    installment_number = Column(Integer, nullable=True)
    amount = Column(Float, nullable=True)
    due_date = Column(String, nullable=True)
    paid_date = Column(String, nullable=True)
    status = Column(String, nullable=True)
    stripe_payment_id = Column(String, nullable=True)
    created_at = Column(String, nullable=True)