"""
Approver model
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean

from .base import Base, SCHEMA_NAME


class Approver(Base):
    """Represents an authorized approver"""
    
    __tablename__ = "approvers"
    __table_args__ = {"schema": SCHEMA_NAME}
    
    approver_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, nullable=False, unique=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    department = Column(String, nullable=False)
    approval_limit = Column(Numeric(10, 2), default=0.00)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Approver(id={self.approver_id}, name='{self.full_name}', limit={self.approval_limit})>"
