"""
Customer model
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import Base, SCHEMA_NAME


class Customer(Base):
    """Represents a customer"""
    
    __tablename__ = "customers"
    __table_args__ = {"schema": SCHEMA_NAME}
    
    customer_id = Column(Integer, primary_key=True, autoincrement=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    phone = Column(String)
    primary_store_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.stores.store_id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    primary_store = relationship("Store", back_populates="customers")
    orders = relationship("Order", back_populates="customer")
    
    def __repr__(self):
        return f"<Customer(id={self.customer_id}, name='{self.first_name} {self.last_name}', email='{self.email}')>"
