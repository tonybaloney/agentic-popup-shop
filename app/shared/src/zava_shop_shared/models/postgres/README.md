# Zava Retail Database - SQLAlchemy ORM Models

This directory contains SQLAlchemy ORM models that map to the `retail` schema in the PostgreSQL database.

## Overview

The models provide a Pythonic interface to interact with the Zava retail database, supporting:
- Type-safe database operations
- Relationship navigation
- Query building with SQLAlchemy's query API
- Async operations with SQLAlchemy 2.0

## Structure

### Core Models

- **`stores.py`** - Retail stores (physical and online)
- **`categories.py`** - Product categories
- **`product_types.py`** - Product types within categories
- **`suppliers.py`** - Supplier/vendor information
- **`products.py`** - Product catalog
- **`customers.py`** - Customer information
- **`orders.py`** - Customer orders
- **`order_items.py`** - Individual items within orders
- **`inventory.py`** - Product inventory levels by store

### Supplier Management

- **`supplier_contracts.py`** - Supplier contracts
- **`supplier_performance.py`** - Supplier performance evaluations
- **`procurement_requests.py`** - Procurement requests

### Administration

- **`company_policies.py`** - Company policies
- **`approvers.py`** - Authorized approvers
- **`notifications.py`** - System notifications

### AI/ML Features

- **`product_embeddings.py`** - Vector embeddings for products (text and images)

## Usage

### Basic Usage

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from models import Base, Product, Category, Supplier

# Create async engine
engine = create_async_engine(
    "postgresql+asyncpg://user:pass@host:port/database",
    echo=True
)

# Create async session factory
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Query products
async with async_session() as session:
    from sqlalchemy import select
    
    # Simple query
    stmt = select(Product).where(Product.discontinued == False)
    result = await session.execute(stmt)
    products = result.scalars().all()
    
    # Join with relationships
    stmt = (
        select(Product, Category, Supplier)
        .join(Product.category)
        .join(Product.supplier)
        .where(Category.category_name == "Electronics")
    )
    result = await session.execute(stmt)
    for product, category, supplier in result:
        print(f"{product.product_name} - {supplier.supplier_name}")
```

### Creating Tables

```python
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

### Relationship Navigation

```python
async with async_session() as session:
    # Load product with all relationships
    stmt = select(Product).where(Product.product_id == 1)
    result = await session.execute(stmt)
    product = result.scalar_one()
    
    # Access relationships
    print(f"Category: {product.category.category_name}")
    print(f"Supplier: {product.supplier.supplier_name}")
    print(f"Type: {product.product_type.type_name}")
    
    # Access inventory across stores
    for inv in product.inventory:
        print(f"Store: {inv.store.store_name}, Stock: {inv.stock_level}")
```

## Schema Information

- **Schema Name**: `retail`
- **Database**: PostgreSQL with pgvector extension
- **Row Level Security**: Enabled on most tables
- **Key Features**:
  - Foreign key constraints
  - Indexes for performance
  - Check constraints for data validation
  - Vector similarity search support

## Integration with Existing Code

These models can be used alongside the existing `supplier_postgres.py` and `finance_postgres.py` modules:

```python
from models import Supplier, Product
from sqlalchemy.ext.asyncio import AsyncSession

async def get_suppliers_orm(session: AsyncSession):
    """Alternative to raw SQL approach using ORM"""
    from sqlalchemy import select
    
    stmt = (
        select(Supplier)
        .where(Supplier.active_status == True)
        .where(Supplier.esg_compliant == True)
        .order_by(Supplier.supplier_rating.desc())
    )
    
    result = await session.execute(stmt)
    return result.scalars().all()
```

## Notes

- **Vector Embeddings**: The embedding fields use `ARRAY(float)` as a fallback. For production use with pgvector, install `pgvector-python` and use `Vector` type from `pgvector.sqlalchemy`.
- **Async Support**: All models work with SQLAlchemy 2.0's async engine and sessions.
- **RLS**: Row Level Security policies are defined in the database and will be enforced when using these models.

## Future Enhancements

- Add pgvector support for similarity searches
- Add SQLAlchemy hybrid properties for computed fields
- Add query methods as class methods for common patterns
- Add validation using SQLAlchemy events
