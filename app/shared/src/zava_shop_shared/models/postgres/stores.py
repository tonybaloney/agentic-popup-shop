"""
Store model
"""

from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base, SCHEMA_NAME


class Store(Base):
    """Represents a retail store (physical or online)"""
    
    __tablename__ = "stores"
    __table_args__ = {"schema": SCHEMA_NAME}
    
    store_id = Column(Integer, primary_key=True, autoincrement=True)
    store_name = Column(String, nullable=False, unique=True)
    rls_user_id = Column(UUID(as_uuid=True), nullable=False)
    is_online = Column(Boolean, nullable=False, default=False)
    
    # Relationships
    customers = relationship("Customer", back_populates="primary_store")
    orders = relationship("Order", back_populates="store")
    order_items = relationship("OrderItem", back_populates="store")
    inventory = relationship("Inventory", back_populates="store")
    
    def __repr__(self):
        return f"<Store(id={self.store_id}, name='{self.store_name}', online={self.is_online})>"
