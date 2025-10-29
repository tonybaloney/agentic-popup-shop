"""
Product Embedding models
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import ARRAY
from datetime import datetime

from .base import Base, SCHEMA_NAME


class ProductDescriptionEmbedding(Base):
    """Represents text embeddings for product descriptions"""
    
    __tablename__ = "product_description_embeddings"
    __table_args__ = {"schema": SCHEMA_NAME}
    
    product_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.products.product_id"), primary_key=True)
    # Using ARRAY(Float) as pgvector's vector type requires the extension
    # In production, you'd use: from pgvector.sqlalchemy import Vector
    # description_embedding = Column(Vector(1536))
    description_embedding = Column(ARRAY(float))  # Fallback for compatibility
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="description_embedding")
    
    def __repr__(self):
        return f"<ProductDescriptionEmbedding(product_id={self.product_id})>"


class ProductImageEmbedding(Base):
    """Represents image embeddings for product images"""
    
    __tablename__ = "product_image_embeddings"
    __table_args__ = {"schema": SCHEMA_NAME}
    
    product_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.products.product_id"), primary_key=True)
    image_url = Column(String, nullable=False)
    # Using ARRAY(Float) as pgvector's vector type requires the extension
    # In production, you'd use: from pgvector.sqlalchemy import Vector
    # image_embedding = Column(Vector(512))
    image_embedding = Column(ARRAY(float))  # Fallback for compatibility
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    product = relationship("Product", back_populates="image_embedding")
    
    def __repr__(self):
        return f"<ProductImageEmbedding(product_id={self.product_id}, url='{self.image_url}')>"
