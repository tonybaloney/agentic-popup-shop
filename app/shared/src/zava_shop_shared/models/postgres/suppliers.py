"""
Supplier model
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, SCHEMA_NAME


class Supplier(Base):
    """Represents a product supplier/vendor"""
    
    __tablename__ = "suppliers"
    __table_args__ = {"schema": SCHEMA_NAME}
    
    supplier_id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_name = Column(String, nullable=False)
    supplier_code = Column(String, nullable=False, unique=True)
    contact_email = Column(String)
    contact_phone = Column(String)
    address_line1 = Column(String)
    address_line2 = Column(String)
    city = Column(String)
    state_province = Column(String)
    postal_code = Column(String)
    country = Column(String, default="USA")
    payment_terms = Column(String, default="Net 30")
    lead_time_days = Column(Integer, default=14)
    minimum_order_amount = Column(Numeric(10, 2), default=0.00)
    bulk_discount_threshold = Column(Numeric(10, 2), default=10000.00)
    bulk_discount_percent = Column(Numeric(5, 2), default=5.00)
    supplier_rating = Column(Numeric(3, 2), default=3.00)
    esg_compliant = Column(Boolean, default=True)
    approved_vendor = Column(Boolean, default=True)
    preferred_vendor = Column(Boolean, default=False)
    active_status = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    products = relationship("Product", back_populates="supplier")
    contracts = relationship("SupplierContract", back_populates="supplier")
    performance_records = relationship("SupplierPerformance", back_populates="supplier")
    procurement_requests = relationship("ProcurementRequest", back_populates="supplier")
    
    def __repr__(self):
        return f"<Supplier(id={self.supplier_id}, name='{self.supplier_name}', code='{self.supplier_code}')>"
