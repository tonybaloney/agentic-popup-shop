"""
Base class for SQLAlchemy models
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Schema name constant
SCHEMA_NAME = "retail"
