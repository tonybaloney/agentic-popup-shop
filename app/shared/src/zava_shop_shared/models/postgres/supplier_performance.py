"""
Supplier Performance model
"""

from sqlalchemy import Column, Integer, String, Numeric, Date, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, SCHEMA_NAME


class SupplierPerformance(Base):
    """Represents supplier performance evaluation"""
    
    __tablename__ = "supplier_performance"
    __table_args__ = {"schema": SCHEMA_NAME}
    
    performance_id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.suppliers.supplier_id"), nullable=False)
    evaluation_date = Column(Date, nullable=False)
    cost_score = Column(Numeric(3, 2), default=3.00)
    quality_score = Column(Numeric(3, 2), default=3.00)
    delivery_score = Column(Numeric(3, 2), default=3.00)
    compliance_score = Column(Numeric(3, 2), default=3.00)
    overall_score = Column(Numeric(3, 2), default=3.00)
    notes = Column(String)
    
    # Relationships
    supplier = relationship("Supplier", back_populates="performance_records")
    
    def __repr__(self):
        return f"<SupplierPerformance(id={self.performance_id}, supplier_id={self.supplier_id}, score={self.overall_score})>"
