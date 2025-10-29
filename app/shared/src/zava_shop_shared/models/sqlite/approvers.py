"""
Approver model for SQLite
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean

from .base import Base


class Approver(Base):
    """Represents an approver for procurement requests"""
    
    __tablename__ = "approvers"
    
    approver_id = Column(Integer, primary_key=True, autoincrement=True)
    employee_id = Column(String, nullable=False, unique=True)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    department = Column(String, nullable=False)
    approval_limit = Column(Numeric(10, 2), default=0.00)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Approver(id={self.approver_id}, name='{self.full_name}', department='{self.department}')>"
