"""
Product Type model
"""

from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, SCHEMA_NAME


class ProductType(Base):
    """Represents a product type within a category"""
    
    __tablename__ = "product_types"
    __table_args__ = {"schema": SCHEMA_NAME}
    
    type_id = Column(Integer, primary_key=True, autoincrement=True)
    category_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.categories.category_id"), nullable=False)
    type_name = Column(String, nullable=False)
    
    # Relationships
    category = relationship("Category", back_populates="product_types")
    products = relationship("Product", back_populates="product_type")
    
    def __repr__(self):
        return f"<ProductType(id={self.type_id}, name='{self.type_name}')>"
