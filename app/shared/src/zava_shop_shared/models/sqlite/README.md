# SQLite ORM Models

This directory contains SQLAlchemy ORM models for the SQLite database schema.

## Overview

The SQLite ORM provides object-relational mapping for all tables in the retail database:

### Core Models

- **Stores**: Retail store locations (online and physical)
- **Categories**: Product categories
- **ProductTypes**: Product types within categories
- **Products**: Product catalog with pricing and supplier information
- **Suppliers**: Vendor/supplier information and ratings
- **Customers**: Customer information
- **Orders**: Customer orders
- **OrderItems**: Line items in orders
- **Inventory**: Stock levels by store

### Procurement Models

- **ProcurementRequests**: Purchase requisition requests
- **Approvers**: Approval authority users
- **SupplierContracts**: Supplier contract details
- **SupplierPerformance**: Supplier performance ratings

### Support Models

- **CompanyPolicies**: Company procurement and order policies
- **Notifications**: Notification system for procurement requests
- **ProductDescriptionEmbedding**: Text embeddings for product descriptions
- **ProductImageEmbedding**: Image embeddings for product images

## Key Differences from PostgreSQL Models

Unlike the PostgreSQL models which use a `retail` schema, the SQLite models operate in the default schema and do not include schema qualification in foreign key references.

## Usage

```python
from app.models.sqlite import (
    Base,
    Product,
    Supplier,
    Order,
    Customer,
    # ... other models
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Create engine and session
engine = create_engine('sqlite:///retail.db')
Base.metadata.create_all(engine)

# Use models
session = Session(engine)
products = session.query(Product).all()
```

## Relationships

All models maintain consistent relationships with proper back_populates declarations for bi-directional navigation:

- Products → Suppliers, Categories, ProductTypes
- Orders → Customers, Stores
- OrderItems → Orders, Products, Stores
- Inventory → Stores, Products
- ProcurementRequests → Products, Suppliers, Notifications
- SupplierContracts → Suppliers
- SupplierPerformance → Suppliers

## Constraints

The models enforce the same business logic constraints as the SQL schema:
- Unique constraints on SKUs, supplier codes, emails, etc.
- Check constraints on numeric ranges (ratings 0-5)
- Foreign key constraints for referential integrity
- Default values for timestamps and status fields
