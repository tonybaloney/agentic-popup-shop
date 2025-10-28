"""
Order model for SQLite
"""

from sqlalchemy import Column, Integer, Date, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class Order(Base):
    """Represents a customer order"""
    
    __tablename__ = "orders"
    
    order_id = Column(Integer, primary_key=True, autoincrement=True)
    customer_id = Column(Integer, ForeignKey("customers.customer_id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False)
    order_date = Column(Date, nullable=False)
    
    # Relationships
    customer = relationship("Customer", back_populates="orders")
    store = relationship("Store", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order")
    
    def __repr__(self):
        return f"<Order(id={self.order_id}, customer_id={self.customer_id}, date={self.order_date})>"
