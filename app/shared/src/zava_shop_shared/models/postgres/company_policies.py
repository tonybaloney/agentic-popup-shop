"""
Company Policy model
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean

from .base import Base, SCHEMA_NAME


class CompanyPolicy(Base):
    """Represents a company policy"""
    
    __tablename__ = "company_policies"
    __table_args__ = {"schema": SCHEMA_NAME}
    
    policy_id = Column(Integer, primary_key=True, autoincrement=True)
    policy_name = Column(String, nullable=False)
    policy_type = Column(String, nullable=False)
    policy_content = Column(String, nullable=False)
    department = Column(String)
    minimum_order_threshold = Column(Numeric(10, 2))
    approval_required = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<CompanyPolicy(id={self.policy_id}, name='{self.policy_name}', type='{self.policy_type}')>"
