"""
Supplier Contract model
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, SCHEMA_NAME


class SupplierContract(Base):
    """Represents a contract with a supplier"""
    
    __tablename__ = "supplier_contracts"
    __table_args__ = {"schema": SCHEMA_NAME}
    
    contract_id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.suppliers.supplier_id"), nullable=False)
    contract_number = Column(String, nullable=False, unique=True)
    contract_status = Column(String, default="active")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date)
    contract_value = Column(Numeric(12, 2))
    payment_terms = Column(String, nullable=False)
    auto_renew = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    supplier = relationship("Supplier", back_populates="contracts")
    
    def __repr__(self):
        return f"<SupplierContract(id={self.contract_id}, number='{self.contract_number}', status='{self.contract_status}')>"
