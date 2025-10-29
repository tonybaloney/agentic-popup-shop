"""
Product model for SQLite
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class Product(Base):
    """Represents a product in the catalog"""
    
    __tablename__ = "products"
    
    product_id = Column(Integer, primary_key=True, autoincrement=True)
    sku = Column(String, nullable=False, unique=True)
    product_name = Column(String, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.category_id"), nullable=False)
    type_id = Column(Integer, ForeignKey("product_types.type_id"), nullable=False)
    supplier_id = Column(Integer, ForeignKey("suppliers.supplier_id"), nullable=False)
    cost = Column(Numeric(10, 2), nullable=False)
    base_price = Column(Numeric(10, 2), nullable=False)
    gross_margin_percent = Column(Numeric(5, 2), default=33.00)
    product_description = Column(String, nullable=False)
    procurement_lead_time_days = Column(Integer, default=14)
    minimum_order_quantity = Column(Integer, default=1)
    discontinued = Column(Boolean, default=False)
    image_url = Column(String, nullable=True)
    
    # Relationships
    category = relationship("Category", back_populates="products")
    product_type = relationship("ProductType", back_populates="products")
    supplier = relationship("Supplier", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    inventory = relationship("Inventory", back_populates="product")
    procurement_requests = relationship("ProcurementRequest", back_populates="product")
    
    def __repr__(self):
        return f"<Product(id={self.product_id}, sku='{self.sku}', name='{self.product_name}')>"
