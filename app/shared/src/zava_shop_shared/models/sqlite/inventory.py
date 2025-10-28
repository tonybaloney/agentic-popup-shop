"""
Inventory model for SQLite
"""

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class Inventory(Base):
    """Represents inventory levels at a store"""
    
    __tablename__ = "inventory"
    
    store_id = Column(Integer, ForeignKey("stores.store_id"), primary_key=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), primary_key=True)
    stock_level = Column(Integer, nullable=False)
    
    # Relationships
    store = relationship("Store", back_populates="inventory")
    product = relationship("Product", back_populates="inventory")
    
    def __repr__(self):
        return f"<Inventory(store_id={self.store_id}, product_id={self.product_id}, stock={self.stock_level})>"
