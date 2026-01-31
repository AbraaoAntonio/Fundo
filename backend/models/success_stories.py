from core.database import Base
from sqlalchemy import Boolean, Column, Float, Integer, String


class Success_stories(Base):
    __tablename__ = "success_stories"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    member_name = Column(String, nullable=False)
    story = Column(String, nullable=False)
    amount_received = Column(Float, nullable=False)
    is_published = Column(Boolean, nullable=False)
    created_at = Column(String, nullable=False)