"""
Supplier Performance model for SQLite
"""

from sqlalchemy import Column, Integer, Date, Numeric, String, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class SupplierPerformance(Base):
    """Represents supplier performance metrics"""
    
    __tablename__ = "supplier_performance"
    
    performance_id = Column(Integer, primary_key=True, autoincrement=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.supplier_id"), nullable=False)
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
        return f"<SupplierPerformance(id={self.performance_id}, supplier_id={self.supplier_id}, date={self.evaluation_date})>"
