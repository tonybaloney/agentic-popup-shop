"""
Notification model
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, SCHEMA_NAME


class Notification(Base):
    """Represents a notification"""
    
    __tablename__ = "notifications"
    __table_args__ = {"schema": SCHEMA_NAME}
    
    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.procurement_requests.request_id"))
    notification_type = Column(String, nullable=False)
    recipient_email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    message = Column(String, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime)
    
    # Relationships
    procurement_request = relationship("ProcurementRequest", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification(id={self.notification_id}, type='{self.notification_type}', to='{self.recipient_email}')>"
