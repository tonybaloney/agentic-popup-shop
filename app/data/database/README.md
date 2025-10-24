# GitHub Popup Stores SQLite Database Generator

This directory contains the SQLite database generator for **GitHub Popup Stores**, a fictional retail company with popup locations across the US. The generator creates a comprehensive sales database with realistic retail data patterns, seasonal variations, and advanced features for data analysis and agentic applications.

## Quick Start

### How to Generate the GitHub Popup Stores SQLite Database

To generate the complete GitHub Popup Stores SQLite database:

```bash
# Navigate to the database directory
cd data/database

pip install -r requirements.txt

# Run the generator (creates complete database)
python generate_github_sqlite_sqlalchemy.py

# Or run with specific options
python generate_github_sqlite_sqlalchemy.py --show-stats          # Show database statistics
python generate_github_sqlite_sqlalchemy.py --embeddings-only     # Populate embeddings only
python generate_github_sqlite_sqlalchemy.py --verify-embeddings   # Verify embeddings table
python generate_github_sqlite_sqlalchemy.py --verify-seasonal     # Verify seasonal patterns
python generate_github_sqlite_sqlalchemy.py --clear-embeddings    # Clear existing embeddings
python generate_github_sqlite_sqlalchemy.py --batch-size 200      # Set embedding batch size
python generate_github_sqlite_sqlalchemy.py --num-customers 100000 # Set number of customers
python generate_github_sqlite_sqlalchemy.py --help                # Show all options
```

**Prerequisites:**

- Python 3.13+ with required packages (sqlalchemy, faker, python-dotenv)
- Required JSON reference files (see Reference Data Files section below)

### Database Schema Reference

The complete database structure is defined in the SQLAlchemy ORM models located in `/workspace/app/models/sqlite/` containing:

- **17 Tables** - Complete retail schema with all column definitions
- **Relationships** - Bi-directional ORM relationships between entities
- **Constraints** - Data integrity constraints (unique, foreign key, check constraints)
- **Default Values** - Automatic timestamp and status field defaults

See the [SQLite Models README](/workspace/app/models/sqlite/README.md) for detailed information about the database structure, models, and relationships.

## Available Tools

This directory contains several utility tools for managing and working with the GitHub Popup Stores database:

### **Core Database Tools**

- **`generate_github_sqlite_sqlalchemy.py`** - Main database generator that creates the complete GitHub Popup Stores retail database with realistic sales data, seasonal patterns, and AI embeddings
- **`count_products.py`** - Analyzes and reports product counts across categories and embedding status from the JSON reference files

### **AI/ML and Embedding Tools**

- **`add_image_embeddings.py`** - Generates image embeddings for product images (stored as serialized strings in SQLite)
- **`add_description_embeddings.py`** - Creates text embeddings for product descriptions (stored as serialized strings in SQLite)
- **`query_by_description.py`** - Interactive search tool that finds products using natural language queries via semantic similarity search
- **`image_generation.py`** - Generates product images using Azure OpenAI DALL-E 3 and updates the JSON file with image paths

### **Data Management Tools**

- **`format_embeddings.py`** - Reformats embedding arrays in JSON files to use compact single-line formatting instead of multi-line arrays

### **Documentation**

- **`README.md`** - This file, documentation for the SQLite database generator
- **See also**: `/workspace/app/models/sqlite/README.md` - Complete SQLite ORM model documentation

### **Reference Data Files**

Located in the `reference_data/` directory:

- **`stores_reference.json`** - Consolidated store configurations, product assignments, and seasonal data
- **`product_data.json`** - Complete product catalog with categories, seasonal multipliers, and AI embeddings  
- **`supplier_data.json`** - Supplier information for retail vendors
- **`seasonal_multipliers.json`** - Seasonal adjustment factors for different climate zones

## Overview

The database generator creates a complete retail ecosystem for GitHub Popup Stores, simulating a multi-store retailer with 16 locations across major US cities, including 15 physical popup stores and 1 online store. The generated data supports advanced analytics, seasonal pattern analysis, multimodal AI applications with both image and text embeddings, and agentic applications.

**Key Features:**
- **Static Reference Data**: All supplier information, contract data, and business-critical values are controlled via JSON files for consistent, predictable database generation
- **Reproducible Results**: Static data ensures identical database content across multiple generations for reliable testing and development

## Generated Database Structure

### Core Tables

The SQLite database contains 17 interconnected tables. For complete details on all models, relationships, and constraints, see the [SQLite Models README](/workspace/app/models/sqlite/README.md).

#### **Stores** (`stores`)

- **16 retail locations** across major US cities:
  - **Physical stores (15)**: NYC Times Square, SF Union Square, Austin Downtown, Denver LoDo, Chicago Loop, Boston Back Bay, Seattle Capitol Hill, Atlanta Midtown, Miami Design District, Portland Pearl District, Nashville Music Row, Phoenix Scottsdale, Minneapolis Mill District, Raleigh Research Triangle, Salt Lake City Downtown
  - **Online store (1)**: GitHub Popup Online Store
- Each store has unique characteristics:
  - Store ID and name
  - RLS user ID for access control  
  - Online/physical store flag
- Relationships with orders, inventory, order items, and customers

#### **Customers** (`customers`)

- **50,000+ customer records** with realistic demographic data
- Customer information: names, emails, phone numbers
- Primary store assignments based on geographic distribution
- Relationships with orders

#### **Product Catalog** (`categories`, `product_types`, `products`)

- **5 main product categories** with comprehensive retail inventory:
  - **Accessories**: Backpacks & Bags, Belts, Caps & Hats, Gloves, Scarves, Socks, Sunglasses
  - **Apparel - Bottoms**: Jeans, Pants, Shorts
  - **Apparel - Tops**: Flannel Shirts, Formal Shirts, Hoodies, Sweatshirts, T-Shirts
  - **Footwear**: Boots, Dress Shoes, Sandals, Sneakers
  - **Outerwear**: Coats, Jackets
- **129 unique products** across 21 product types
- **Product hierarchy**: Categories → Product Types → Individual Products
- **Cost and pricing structure** with consistent 33% gross margin
- **Complete product specifications**: SKUs, descriptions, pricing
- **Supplier integration**: Full procurement workflow with 20 suppliers using static contract data for consistent results
- Relationships with categories, product types, suppliers, order items, inventory, and embeddings

#### **Orders & Sales** (`orders`, `order_items`)

- **Historical transaction data** spanning 2020-2026
- **Order header** information: customer, store, date, status
- **Detailed line items**: products, quantities, prices, discounts
- **Variable order patterns** based on store characteristics and seasonality
- Relationships with customers, stores, and products

#### **Inventory** (`inventory`)

- **Store-specific stock levels** for all products
- **Seasonal inventory adjustments** based on demand patterns
- **Geographic distribution** reflecting local market preferences
- Relationships with stores and products

#### **Suppliers** (`suppliers`)

- **20 supplier profiles** with complete static data
- Supplier information: names, codes, contact details
- ESG compliance status, ratings, lead times
- Relationships with products, contracts, and performance records

#### **Procurement & Business Logic**

Additional tables for complete business operations:
- **`procurement_requests`** - Purchase requisition workflow
- **`approvers`** - Approval authority definitions
- **`supplier_contracts`** - Contract management
- **`supplier_performance`** - Supplier evaluation and ratings
- **`company_policies`** - Business rules and approval policies
- **`notifications`** - System notifications

#### **Product Embeddings** (`product_image_embeddings`, `product_description_embeddings`)

- **AI ready vector embeddings** stored as serialized strings in SQLite
- **Image embeddings**: Product visual features for image-based search
- **Description embeddings**: Text features for semantic search
- **Similarity search capabilities** for recommendation systems (requires deserialization)
- Relationships with products

For complete details on all 17 tables, their fields, constraints, and relationships, see the [SQLite Models README](/workspace/app/models/sqlite/README.md).

## Key Data Features

### 📊 Seasonal Variations

The generator implements **multi-zone seasonal multipliers** across three climate zones for realistic business patterns:

#### **🌲 Pacific Northwest Zone** (Seattle, Portland)
- **Outerwear**: Peak winter demand (1.8x), low summer (0.6x)
- **Apparel - Tops**: Summer peak (1.4x), winter low (0.6x)
- **Pattern**: Mild, wet winters and dry summers

#### **🌡️ Temperate Zone** (NYC, Denver, Chicago, Boston, Nashville, Minneapolis, Raleigh, Salt Lake City)
- **Outerwear**: Strong winter pattern (1.6x), minimal summer (0.5x)
- **Apparel - Tops**: Summer focused (1.3x), winter low (0.7x)
- **Pattern**: Moderate seasonal variation with distinct seasons

#### **☀️ Warm Zone** (SF, Austin, Atlanta, Miami, Phoenix)
- **Outerwear**: Mild winter demand (1.3x), very low summer (0.4x)
- **Apparel - Tops**: Strong summer demand (1.4x)
- **Pattern**: Milder winters, hot summers

#### **Seasonal Business Intelligence**
- **Outerwear** shows strongest seasonal variation (0.4x to 1.8x multipliers)
- **Apparel - Bottoms** maintain stable year-round demand
- **Q4 (Oct-Dec)** universally strong for outerwear and accessories

### 💰 Financial Structure

#### **Margin Analysis**

- **Consistent 33% gross margin** across all products
- **Cost basis**: JSON price data represents wholesale cost
- **Selling price calculation**: Cost ÷ 0.67 = Retail Price
- **Margin verification**: Built-in reporting and validation

#### **Revenue Patterns**

- **Year-over-year growth**: Configurable growth patterns (2020-2026) with consistent business expansion
- **Growth trajectory**: Steady increases year-over-year, except for 2023 which shows a slight decline reflecting market conditions
- **Store performance variation**: Based on location and market size
- **Seasonal revenue fluctuations**: Aligned with product demand cycles

### 🏪 Store Performance Characteristics

#### **High-Performance Stores**

- **NYC Times Square**: Premium urban location with high traffic
- **SF Union Square**: West coast flagship with strong performance
- **Online Store**: Complete product catalog (129 products) vs curated physical store selection (40-55 products)

#### **Geographic Distribution**

- **15 major US cities** with themed popup locations
- **Strategic positioning**: Tech hubs, cultural districts, downtown cores
- **Market coverage**: East Coast, West Coast, Mountain West, Midwest, South
- **Climate-aware inventory**: Seasonal product mix based on local weather patterns

#### **Store Performance Characteristics**

- **Physical stores**: 40-55 curated products (~30% of total catalog)
- **Online store**: Complete product catalog access
- **Product overlap**: ~20-30% core essentials shared across stores
- **Unique assortment**: 70-80% store-specific products based on local themes

### 🔒 Security & Access Control

#### **Store Manager Isolation**

- **RLS User IDs**: Each store has a unique RLS user ID for access control
- **Multi-tenancy support**: Store-specific data can be isolated in application logic
- **Controlled access** to reference data (products, categories)

#### **Manager Access Patterns**

- **Unique UUIDs** for each store manager stored in the stores table
- **Application-level data isolation** between stores
- **Super manager access**: UUID `00000000-0000-0000-0000-000000000000` for administrative access

### 🚀 Advanced Features

#### **Vector Search Capabilities**

- **Embedding storage**: Product image and description embeddings stored as serialized strings
- **Product image embeddings** for visual recommendation engines
- **Product description embeddings** for semantic text search
- **Application-level similarity**: Embeddings can be deserialized for use in Python/ML applications
- **Dual embedding support** ready for multimodal ML applications

#### **Performance Optimization**

- **SQLite optimizations**: Proper indexing strategy for common query patterns
- **Foreign key constraints**: Referential integrity maintained at database level
- **Batch insert operations** for large data volumes
- **Efficient querying** with ORM relationships

#### **Data Quality & Validation**

- **Built-in verification** routines for data consistency
- **Seasonal pattern validation** and reporting
- **Margin analysis** and financial reconciliation
- **Statistical summaries** and health checks

## Technical Requirements

- **Python 3.13+** with sqlalchemy, faker, python-dotenv
- **SQLite 3**: Built-in with Python, no separate installation required
- **Memory**: Recommended 2GB+ for large datasets
- **Storage**: ~500MB for complete database with embeddings

## Reference Data Files

### `reference_data/stores_reference.json`

- Consolidated store configurations and product assignments
- Store location data with climate zone assignments
- Customer distribution weights and performance multipliers
- Store manager RLS UUID mappings
- Product assignments for each store

### `reference_data/product_data.json`

- Complete product catalog with categories and types
- Product specifications, pricing, and descriptions
- Image and description embedding data for AI/ML applications
- SKUs and supplier relationships

### `reference_data/supplier_data.json`

- **20 supplier profiles** with complete static data for consistent database generation
- **Static supplier information**: IDs, names, codes, and contact details
- **Contract management**: Contract numbers, values, and end dates
- **Procurement workflow**: ESG compliance status, vendor approval data, bulk discount thresholds, payment terms, performance ratings, and lead times
- **Consistent data generation**: All supplier-related fields use static values from JSON instead of random generation

### `reference_data/seasonal_multipliers.json`

- Climate zone definitions (Pacific Northwest, Temperate, Warm)
- Monthly seasonal multipliers by category and zone
- Store-to-climate-zone mappings

## Data Volume Summary

| Component | Count | Description |
|-----------|-------|-------------|
| **Customers** | 20,000+ | Realistic demographic profiles across 15 US cities and online |
| **Products** | 129 | Complete retail catalog (accessories, apparel, footwear, outerwear) |
| **Stores** | 16 | 15 physical popup stores + 1 online store across major US cities |
| **Suppliers** | 20 | Complete supplier directory with static contract data and procurement workflow |
| **Orders** | 50,000+ | Multi-year transaction history with detailed sales data |
| **Inventory Items** | 480 | Store-specific inventory across multiple locations |
| **Image Embeddings** | 129 | AI embeddings stored as serialized strings (when populated) |
| **Description Embeddings** | 129 | AI embeddings stored as serialized strings (when populated) |

This database provides a realistic foundation for retail analytics, machine learning experimentation, seasonal trend analysis, and multi-tenant application development in the retail industry. The SQLite database with serialized embeddings enables advanced AI-powered product similarity searches, comprehensive sales analytics, and sophisticated procurement workflows.

## JSON Data File Schemas

The generator requires two JSON configuration files that define the product catalog and store configurations:

### `reference_data/product_data.json` Schema

Defines the complete product catalog with embeddings and seasonal patterns:

```json
{
  "main_categories": {
    "<CATEGORY_NAME>": {
      "<PRODUCT_TYPE>": [
        {
          "name": "string",                    // Product display name
          "sku": "string",                     // Unique product identifier
          "price": number,                     // Base cost price
          "description": "string",             // Product description
          "stock_level": number,               // Base inventory level
          "image_path": "string",              // Relative path to product image
          "image_embedding": [float, ...],     // 512-dimension image vector embedding
          "description_embedding": [float, ...] // 1536-dimension text vector embedding
        }
      ]
    }
  }
}
```

**Key Points:**

- **`image_embedding`: Serialized embedding array for image similarity search
- **`description_embedding`**: Serialized embedding array for text similarity search
- `price`: The actual retail store selling price; cost is calculated backwards using 33% gross margin (Cost = Price × 0.67)
- Each category can contain multiple product types, each with an array of products
- Seasonal multipliers are now defined separately in `seasonal_multipliers.json`

### `reference_data/stores_reference.json` Schema

Defines store configurations and business rules:

```json
{
  "stores": {
    "<STORE_NAME>": {
      "rls_user_id": "uuid",                  // Row Level Security identifier
      "customer_distribution_weight": number, // Relative customer allocation weight
      "order_frequency_multiplier": number,   // Order frequency scaling factor
      "order_value_multiplier": number        // Order value scaling factor
    }
  },
  "year_weights": {
    "<YEAR>": number                          // Growth pattern weights by year
  }
}
```

**Key Points:**

- `rls_user_id`: UUID for Row Level Security policies (store manager access control)
- Distribution weights: Control customer and sales allocation across stores
- Order multipliers: Scale order frequency and value by store characteristics
- Year weights: Create realistic business growth patterns over time (2020-2026)

### `reference_data/supplier_data.json` Schema

Defines comprehensive supplier profiles with static contract data for consistent database generation:

```json
{
  "<SUPPLIER_ID>": {
    "supplier_id": number,                    // Sequential supplier ID (1-20)
    "supplier_name": "string",               // Company name
    "supplier_code": "string",               // Standard format: SUP001-SUP020
    "contact_email": "string",               // Primary contact email
    "contact_phone": "string",               // Primary contact phone
    "contracts": [
      {
        "contract_id": number,               // Contract identifier
        "contract_number": "string",         // Format: 2024-XXXX-NNN
        "contract_value": number,            // Contract value (rounded to $10K)
        "start_date": "YYYY-MM-DD",          // Contract start date
        "end_date": "YYYY-MM-DD",            // Contract end date (1-2 years)
        "contract_status": "active",         // Contract status
        "payment_terms": "string",           // Payment terms (Net 30/45/60)
        "auto_renew": boolean,               // Auto-renewal flag
        "contract_created": "ISO datetime",  // Creation timestamp
        "renewal_due_soon": boolean,         // Renewal alert flag
        "days_until_expiry": number          // Calculated days to expiry
      }
    ]
  }
}
```

**Key Points:**

- **Static Data Control**: All supplier information is now static and controlled via JSON instead of random generation
- **Contract Values**: Rounded to nearest $10,000 ranging from $50K to $600K for realistic contract sizes
- **Contract Dates**: End dates range between 1-2 years from current date for realistic contract terms
- **Contract Numbers**: Follow standard format `2024-XXXX-NNN` for consistent naming convention
- **Supplier Codes**: Sequential format `SUP001` through `SUP020` for easy identification
- **Supplier IDs**: Sequential integers 1-20 matching database primary keys
- **Database Consistency**: Generator uses these static values to ensure identical data across database recreations

### Database Connection Configuration

The generator creates a SQLite database file:

- **Database File**: `retail.db` (or custom path)
- **Schema**: All tables in the default SQLite schema
- **Connection**: SQLite file-based, no server required
- **ORM**: SQLAlchemy with declarative models in `/workspace/app/models/sqlite/`

Configuration can be customized using environment variables or a `.env` file.

## Database Schema Reference

The complete database schema is defined using SQLAlchemy ORM models in `/workspace/app/models/sqlite/`. This directory contains Python class definitions for all database tables and their relationships.

### Schema Highlights

#### **Core Tables (17 total)**
- `stores` - Store locations with RLS user mappings
- `customers` - Customer profiles with store associations
- `categories` - Product category hierarchy
- `product_types` - Product type definitions within categories
- `products` - Complete product catalog with supplier relationships
- `suppliers` - Supplier directory with procurement terms
- `orders` - Order header information
- `order_items` - Detailed line items for each order
- `inventory` - Store-specific stock levels
- `supplier_performance` - Supplier evaluation and ratings
- `procurement_requests` - Purchase requisition workflow
- `company_policies` - Business rules and approval policies
- `supplier_contracts` - Contract management
- `approvers` - Approval authority definitions
- `notifications` - System notifications
- `product_image_embeddings` - AI image embeddings (serialized)
- `product_description_embeddings` - AI text embeddings (serialized)

#### **Advanced Features**
- **ORM Relationships**: Bi-directional relationships for easy data navigation
- **Constraints**: Foreign keys, unique constraints, and check constraints
- **Default Values**: Automatic timestamps and status fields
- **Type Safety**: SQLAlchemy types for data validation

#### **Usage**
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.models.sqlite import Base, Product, Store, Order

# Create/connect to database
engine = create_engine('sqlite:///retail.db')
Base.metadata.create_all(engine)

# Query data
session = Session(engine)
products = session.query(Product).all()
```

For complete documentation of all models, relationships, and usage examples, see:
- [SQLite Models README](/workspace/app/models/sqlite/README.md) - Complete model documentation
- `/workspace/app/models/sqlite/` - Individual model files with detailed implementations
