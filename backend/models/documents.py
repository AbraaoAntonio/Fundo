from core.database import Base
from sqlalchemy import Column, Integer, String


class Documents(Base):
    __tablename__ = "documents"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True, autoincrement=True, nullable=False)
    user_id = Column(String, nullable=False)
    request_id = Column(Integer, nullable=True)
    document_type = Column(String, nullable=True)
    file_name = Column(String, nullable=True)
    file_url = Column(String, nullable=True)
    uploaded_at = Column(String, nullable=True)