from core.database import Base
from sqlalchemy import Column, Integer, String


class Admins(Base):
    __tablename__ = "admins"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    user_id = Column(String, nullable=False)
    email = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(String, nullable=False)