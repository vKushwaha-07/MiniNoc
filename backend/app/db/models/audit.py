from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.db.session import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # Who did it?
    user = Column(String, default="admin")  # Placeholder until real Auth is implemented
    
    # What did they do?
    action = Column(String, index=True)      # e.g., "WAKE_DEVICE", "DELETE_DEVICE"
    resource = Column(String, index=True)    # e.g., "192.168.1.50"
    
    # Details
    details = Column(Text, nullable=True)    # Human readable summary
    metadata_json = Column(JSON, nullable=True)   # Tech details (params, raw response)
