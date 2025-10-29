"""
Category model for SQLite
"""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from .base import Base


class Category(Base):
    """Represents a product category"""
    
    __tablename__ = "categories"
    
    category_id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String, nullable=False, unique=True)
    
    # Relationships
    products = relationship("Product", back_populates="category")
    product_types = relationship("ProductType", back_populates="category")
    
    def __repr__(self):
        return f"<Category(id={self.category_id}, name='{self.category_name}')>"
