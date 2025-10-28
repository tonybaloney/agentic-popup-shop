"""
Order Item model for SQLite
"""

from sqlalchemy import Column, Integer, Numeric, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class OrderItem(Base):
    """Represents a line item in an order"""
    
    __tablename__ = "order_items"
    
    order_item_id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey("orders.order_id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.store_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.product_id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)
    discount_percent = Column(Integer, default=0)
    discount_amount = Column(Numeric(10, 2), default=0.00)
    total_amount = Column(Numeric(10, 2), nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")
    store = relationship("Store", back_populates="order_items")
    
    def __repr__(self):
        return f"<OrderItem(id={self.order_item_id}, order_id={self.order_id}, product_id={self.product_id})>"
