"""
Procurement Request model
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, SCHEMA_NAME


class ProcurementRequest(Base):
    """Represents a procurement request"""
    
    __tablename__ = "procurement_requests"
    __table_args__ = {"schema": SCHEMA_NAME}
    
    request_id = Column(Integer, primary_key=True, autoincrement=True)
    request_number = Column(String, nullable=False, unique=True)
    requester_name = Column(String, nullable=False)
    requester_email = Column(String, nullable=False)
    department = Column(String, nullable=False)
    product_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.products.product_id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.suppliers.supplier_id"), nullable=False)
    quantity_requested = Column(Integer, nullable=False)
    unit_cost = Column(Numeric(10, 2), nullable=False)
    total_cost = Column(Numeric(10, 2), nullable=False)
    justification = Column(String)
    urgency_level = Column(String, default="Normal")
    approval_status = Column(String, default="Pending")
    approved_by = Column(String)
    approved_at = Column(DateTime)
    request_date = Column(DateTime, default=datetime.utcnow)
    required_by_date = Column(Date)
    vendor_restrictions = Column(String)
    esg_requirements = Column(Boolean, default=False)
    bulk_discount_eligible = Column(Boolean, default=False)
    
    # Relationships
    product = relationship("Product", back_populates="procurement_requests")
    supplier = relationship("Supplier", back_populates="procurement_requests")
    notifications = relationship("Notification", back_populates="procurement_request")
    
    def __repr__(self):
        return f"<ProcurementRequest(id={self.request_id}, number='{self.request_number}', status='{self.approval_status}')>"
