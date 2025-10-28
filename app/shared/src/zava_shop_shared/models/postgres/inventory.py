"""
Inventory model
"""

from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, SCHEMA_NAME


class Inventory(Base):
    """Represents inventory levels for products at stores"""
    
    __tablename__ = "inventory"
    __table_args__ = {"schema": SCHEMA_NAME}
    
    store_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.stores.store_id"), primary_key=True)
    product_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.products.product_id"), primary_key=True)
    stock_level = Column(Integer, nullable=False)
    
    # Relationships
    store = relationship("Store", back_populates="inventory")
    product = relationship("Product", back_populates="inventory")
    
    def __repr__(self):
        return f"<Inventory(store_id={self.store_id}, product_id={self.product_id}, stock={self.stock_level})>"
