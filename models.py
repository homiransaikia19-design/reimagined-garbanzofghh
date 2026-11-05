from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database import Base
import datetime

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key_string = Column(String, unique=True, index=True)
    owner_name = Column(String)
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    total_requests = Column(Integer, default=0)