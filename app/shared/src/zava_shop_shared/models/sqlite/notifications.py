"""
Notification model for SQLite
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base


class Notification(Base):
    """Represents a notification"""
    
    __tablename__ = "notifications"
    
    notification_id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, ForeignKey("procurement_requests.request_id"))
    notification_type = Column(String, nullable=False)  # approval_request, status_update, completion
    recipient_email = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    message = Column(String, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime)
    
    # Relationships
    procurement_request = relationship("ProcurementRequest", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification(id={self.notification_id}, type='{self.notification_type}', recipient='{self.recipient_email}')>"
