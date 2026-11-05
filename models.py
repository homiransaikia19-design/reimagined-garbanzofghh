from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class APIKey(Base):
    __tablename__ = "api_keys"
    id = Column(Integer, primary_key=True, index=True)
    key_string = Column(String(100), unique=True, index=True)
    owner_name = Column(String(255))
    expires_at = Column(DateTime)
    is_active = Column(Boolean, default=True)
    request_limit = Column(Integer, default=1000)
    
    # This tells the database to delete usage logs if the API key is deleted
    logs = relationship("APIUsageLog", backref="api_key", cascade="all, delete-orphan")

class APIUsageLog(Base):
    __tablename__ = "api_usage_logs"
    id = Column(Integer, primary_key=True, index=True)
    api_key_id = Column(Integer, ForeignKey("api_keys.id"))
    usage_date = Column(Date)
    hit_count = Column(Integer, default=0)