from core.database import Base
from sqlalchemy import Column, Integer, String


class Class_upgrades(Base):
    __tablename__ = "class_upgrades"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    user_id = Column(String, nullable=False)
    profile_id = Column(Integer, nullable=True)
    from_class = Column(String, nullable=True)
    to_class = Column(String, nullable=True)
    status = Column(String, nullable=True)
    payments_in_new_class = Column(Integer, nullable=True)
    requested_at = Column(String, nullable=True)
    activated_at = Column(String, nullable=True)