"""
Customer Sales Database Generator for PostgreSQL with pgvector

This script generates a comprehensive customer sales database with optimized indexing
and vector embeddings support for PostgreSQL with pgvector extension.

DATA FILE STRUCTURE (all in reference_data/ folder):
- stores_reference.json: Consolidated store configurations, product assignments, and seasonal data
- product_data.json: Contains all product information (main_categories with products)
- supplier_data.json: Contains supplier information for clothing/apparel vendors
- seasonal_multipliers.json: Contains seasonal adjustment factors for different climate zones

POSTGRESQL CONNECTION:
- Requires PostgreSQL with pgvector extension enabled
- Uses async connections via asyncpg
- Targets retail schema in zava database

FEATURES:
- Complete database generation with customers, products, stores, orders
- Product image embeddings population from product_data.json
- Product description embeddings population from product_data.json
- Vector similarity indexing with pgvector
- Performance-optimized indexes
- Comprehensive statistics and verification
- Reproducible store product assignments (via store_products.json)

USAGE:
    python generate_zava_postgres.py                     # Generate complete database
    python generate_zava_postgres.py --show-stats        # Show database statistics
    python generate_zava_postgres.py --embeddings-only   # Populate embeddings only
    python generate_zava_postgres.py --verify-embeddings # Verify embeddings table
    python generate_zava_postgres.py --help              # Show all options
"""

import argparse
import asyncio
import json
import logging
import os
import random
import subprocess
import sys
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import asyncpg
from dotenv import load_dotenv
from faker import Faker

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
# Try to load .env from script directory first, then parent directories
env_paths = [
    os.path.join(script_dir, '.env'),
    os.path.join(script_dir, '..', '..', '..', '.env'),  # Up to workspace root
]

for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break
else:
    # Fallback to default behavior
    load_dotenv()

# Initialize Faker and logging
fake = Faker()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Reference data file constants
REFERENCE_DATA_DIR = 'reference_data'
STORES_REFERENCE_FILE = 'stores_reference.json'
PRODUCT_DATA_FILE = 'product_data.json'
SUPPLIER_DATA_FILE = 'supplier_data.json' 
SEASONAL_MULTIPLIERS_FILE = 'seasonal_multipliers.json'

# PostgreSQL connection configuration
POSTGRES_CONFIG = {
    'host': os.getenv('POSTGRES_DB_HOST', '192.168.1.16'),
    'port': int(os.getenv('POSTGRES_DB_PORT', '5432')),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'change-me'),
    'database': os.getenv('POSTGRES_DB', 'zava')
}

SCHEMA_NAME = 'retail'

# Super Manager UUID - has access to all rows regardless of RLS policies
SUPER_MANAGER_UUID = '00000000-0000-0000-0000-000000000000'

# Load reference data from JSON file
def load_reference_data():
    """Load reference data from consolidated stores_reference.json file"""
    try:
        consolidated_path = os.path.join(os.path.dirname(__file__), REFERENCE_DATA_DIR, STORES_REFERENCE_FILE)
        with open(consolidated_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load {REFERENCE_DATA_DIR}/{STORES_REFERENCE_FILE}: {e}")
        raise

def load_seasonal_multipliers():
    """Load seasonal multipliers configuration"""
    try:
        seasonal_path = os.path.join(os.path.dirname(__file__), REFERENCE_DATA_DIR, SEASONAL_MULTIPLIERS_FILE)
        with open(seasonal_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.warning(f"Failed to load seasonal multipliers: {e}")
        return None

def load_product_data():
    """Load product data from JSON file"""
    try:
        json_path = os.path.join(os.path.dirname(__file__), REFERENCE_DATA_DIR, PRODUCT_DATA_FILE)
        with open(json_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Failed to load product data: {e}")
        raise

# Load the reference data
reference_data = load_reference_data()
product_data = load_product_data()
seasonal_config = load_seasonal_multipliers()

# Get reference data from loaded JSON
main_categories = product_data['main_categories']
stores = reference_data['stores']

# Global variable for supplier category mapping
SUPPLIER_CATEGORY_MAP = {}

# Load store products configuration
def load_store_products():
    """Load store products configuration - now integrated into stores_reference.json"""
    try:
        # Products are now part of the consolidated stores_reference.json file
        # No need for separate loading - return None to indicate integrated format
        return None
    except Exception as e:
        logging.warning(f"Error in store products loading: {e}")
        return None

store_products_config = load_store_products()

# Check if seasonal trends are available
seasonal_categories = []
if seasonal_config and 'climate_zones' in seasonal_config:
    # Get categories from the multi-zone seasonal config
    for climate_zone, zone_data in seasonal_config['climate_zones'].items():
        for category_name in zone_data.get('categories', {}).keys():
            if category_name not in seasonal_categories:
                seasonal_categories.append(category_name)
    logging.info(f"🗓️  Multi-zone seasonal trends active for {len(seasonal_categories)} categories across {len(seasonal_config['climate_zones'])} climate zones")
    logging.info(f"    Categories: {', '.join(seasonal_categories)}")
    logging.info(f"    Climate zones: {', '.join(seasonal_config['climate_zones'].keys())}")
else:
    logging.info("⚠️  No seasonal trends found - using equal weights for all categories")

def get_store_name_from_id(store_id: str) -> str:
    """Get store name from store ID"""
    if store_id in stores:
        return stores[store_id].get('store_name', store_id)
    # Fallback: assume store_id is already a store name (for backward compatibility)
    return store_id

def get_store_id_from_name(store_name: str) -> str:
    """Get store ID from store name"""
    for store_id, config in stores.items():
        if config.get('store_name') == store_name:
            return store_id
    # Fallback: assume store_name is already a store ID (for backward compatibility)
    return store_name

def is_using_store_ids() -> bool:
    """Check if we're using the new ID-based format"""
    # Check if the first store has a 'store_name' field (new format) vs being the key itself (old format)  
    first_store_key = next(iter(stores.keys()))
    return 'store_name' in stores[first_store_key]

def weighted_store_choice():
    """Choose a store based on weighted distribution"""
    store_keys = list(stores.keys())
    weights = [stores[store]['customer_distribution_weight'] for store in store_keys]
    selected_key = random.choices(store_keys, weights=weights, k=1)[0]
    
    # Return store name for backward compatibility
    if is_using_store_ids():
        return get_store_name_from_id(selected_key)
    else:
        return selected_key

def generate_phone_number(region=None):
    """Generate a phone number in North American format (XXX) XXX-XXXX"""
    return f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"

def get_seasonal_multipliers_for_store_and_category(store_name: str, category: str) -> List[float]:
    """Get seasonal multipliers for a specific store and category"""
    try:
        # Get store configuration (handle both ID-based and name-based formats)
        store_config = None
        if is_using_store_ids():
            # New ID-based format: find store by ID or name
            store_id = get_store_id_from_name(store_name)
            store_config = stores.get(store_id, {})
        else:
            # Old format: store_name is the key
            store_config = stores.get(store_name, {})
        
        if not store_config:
            logging.warning(f"Store config not found for {store_name}")
            return [1.0] * 12
        
        # Use the multi-zone seasonal config
        if seasonal_config and 'climate_zones' in seasonal_config:
            location = store_config.get('location', {})
            climate_zone = location.get('climate_zone', 'temperate')
            
            climate_zones = seasonal_config.get('climate_zones', {})
            zone_config = climate_zones.get(climate_zone, {})
            category_multipliers = zone_config.get('categories', {})
            
            return category_multipliers.get(category, [1.0] * 12)
        
        # Check if we have simple seasonal multipliers in reference data (consolidated format)
        if 'seasonal_multipliers' in reference_data:
            location = store_config.get('location', {})
            climate_zone = location.get('climate_zone', 'temperate')
            
            if climate_zone in reference_data['seasonal_multipliers']:
                return reference_data['seasonal_multipliers'][climate_zone]
        
        # Default to no seasonal variation
        return [1.0] * 12
    except Exception as e:
        logging.warning(f"Error getting seasonal multipliers for {store_name}/{category}: {e}")
        return [1.0] * 12

async def create_connection():
    """Create async PostgreSQL connection"""
    try:
        conn = await asyncpg.connect(**POSTGRES_CONFIG)
        logging.info(f"Connected to PostgreSQL at {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}")
        return conn
    except Exception as e:
        logging.error(f"Failed to connect to PostgreSQL: {e}")
        raise

async def create_database_schema(conn):
    """Create database schema from SQL file using psql"""
    try:
        logging.info("Loading database schema from SQL file...")
        
        # Get the path to the SQL file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        sql_file_path = os.path.join(script_dir, "github_retail_schema.sql")
        
        if not os.path.exists(sql_file_path):
            raise FileNotFoundError(f"Schema SQL file not found at: {sql_file_path}")
        
        # Get database connection parameters
        host = POSTGRES_CONFIG['host']
        port = POSTGRES_CONFIG['port']
        user = POSTGRES_CONFIG['user']
        password = POSTGRES_CONFIG['password']
        database = POSTGRES_CONFIG['database']
        
        # Construct psql command to execute the schema
        psql_command = [
            "psql",
            f"--host={host}",
            f"--port={port}",
            f"--username={user}",
            f"--dbname={database}",
            "--quiet",  # Reduce output noise
            "--file", sql_file_path
        ]
        
        # Set password via environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = password
        
        # Execute the SQL file using psql
        logging.info(f"Executing schema from {sql_file_path}...")
        result = subprocess.run(
            psql_command,
            env=env,
            capture_output=True,
            text=True,
            check=False  # Don't raise exception on non-zero exit
        )
        
        if result.returncode != 0:
            logging.error(f"Error executing schema SQL: {result.stderr}")
            raise RuntimeError(f"Failed to execute schema SQL file: {result.stderr}")
        
        if result.stdout.strip():
            logging.info(f"Schema execution output: {result.stdout}")
        
        logging.info("Database schema created successfully from SQL file!")
        
        # Set up Row Level Security policies that aren't in the SQL dump
        await setup_row_level_security_policies(conn)
        
        # Grant permissions to store_manager role
        await setup_store_manager_permissions(conn)
        
    except Exception as e:
        logging.error(f"Error creating database schema: {e}")
        raise
        await conn.execute(f"""
            CREATE POLICY all_users_categories ON {SCHEMA_NAME}.categories
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Product types table - all users can see all product types
        await conn.execute(f"DROP POLICY IF EXISTS all_users_product_types ON {SCHEMA_NAME}.product_types")
        await conn.execute(f"""
            CREATE POLICY all_users_product_types ON {SCHEMA_NAME}.product_types
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Products table - all users can see all products
        await conn.execute(f"DROP POLICY IF EXISTS all_users_products ON {SCHEMA_NAME}.products")
        await conn.execute(f"""
            CREATE POLICY all_users_products ON {SCHEMA_NAME}.products
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Product image embeddings table - all users can see all product image embeddings
        await conn.execute(f"DROP POLICY IF EXISTS all_users_product_image_embeddings ON {SCHEMA_NAME}.product_image_embeddings")
        await conn.execute(f"""
            CREATE POLICY all_users_product_image_embeddings ON {SCHEMA_NAME}.product_image_embeddings
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Product description embeddings table - all users can see all product description embeddings
        await conn.execute(f"DROP POLICY IF EXISTS all_users_product_description_embeddings ON {SCHEMA_NAME}.product_description_embeddings")
        await conn.execute(f"""
            CREATE POLICY all_users_product_description_embeddings ON {SCHEMA_NAME}.product_description_embeddings
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Suppliers table - all users can see all suppliers (needed for procurement)
        await conn.execute(f"DROP POLICY IF EXISTS all_users_suppliers ON {SCHEMA_NAME}.suppliers")
        await conn.execute(f"""
            CREATE POLICY all_users_suppliers ON {SCHEMA_NAME}.suppliers
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Supplier performance table - all users can see all supplier performance data
        await conn.execute(f"DROP POLICY IF EXISTS all_users_supplier_performance ON {SCHEMA_NAME}.supplier_performance")
        await conn.execute(f"""
            CREATE POLICY all_users_supplier_performance ON {SCHEMA_NAME}.supplier_performance
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Procurement requests table - all users can see all procurement requests (for collaboration)
        await conn.execute(f"DROP POLICY IF EXISTS all_users_procurement_requests ON {SCHEMA_NAME}.procurement_requests")
        await conn.execute(f"""
            CREATE POLICY all_users_procurement_requests ON {SCHEMA_NAME}.procurement_requests
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        logging.info("Row Level Security policies created successfully!")
        
        # Grant permissions to store_manager role
        await setup_store_manager_permissions(conn)
        
        logging.info("Database schema created successfully!")
    except Exception as e:
        logging.error(f"Error creating database schema: {e}")
        raise

async def setup_row_level_security_policies(conn):
    """Setup Row Level Security policies for the database"""
    try:
        logging.info("Setting up Row Level Security policies...")
        logging.info(f"Super Manager UUID (access to all rows): {SUPER_MANAGER_UUID}")
        
        # Enable RLS on tables that should be restricted by store manager
        await conn.execute(f"ALTER TABLE {SCHEMA_NAME}.orders ENABLE ROW LEVEL SECURITY")
        await conn.execute(f"ALTER TABLE {SCHEMA_NAME}.order_items ENABLE ROW LEVEL SECURITY")
        await conn.execute(f"ALTER TABLE {SCHEMA_NAME}.inventory ENABLE ROW LEVEL SECURITY")
        await conn.execute(f"ALTER TABLE {SCHEMA_NAME}.customers ENABLE ROW LEVEL SECURITY")
        
        # Enable RLS on reference tables that store managers should have full access to
        await conn.execute(f"ALTER TABLE {SCHEMA_NAME}.stores ENABLE ROW LEVEL SECURITY")
        await conn.execute(f"ALTER TABLE {SCHEMA_NAME}.categories ENABLE ROW LEVEL SECURITY") 
        await conn.execute(f"ALTER TABLE {SCHEMA_NAME}.product_types ENABLE ROW LEVEL SECURITY")
        await conn.execute(f"ALTER TABLE {SCHEMA_NAME}.suppliers ENABLE ROW LEVEL SECURITY")
        await conn.execute(f"ALTER TABLE {SCHEMA_NAME}.products ENABLE ROW LEVEL SECURITY")
        await conn.execute(f"ALTER TABLE {SCHEMA_NAME}.product_image_embeddings ENABLE ROW LEVEL SECURITY")
        await conn.execute(f"ALTER TABLE {SCHEMA_NAME}.product_description_embeddings ENABLE ROW LEVEL SECURITY")
        await conn.execute(f"ALTER TABLE {SCHEMA_NAME}.supplier_performance ENABLE ROW LEVEL SECURITY")
        await conn.execute(f"ALTER TABLE {SCHEMA_NAME}.procurement_requests ENABLE ROW LEVEL SECURITY")
        
        # Create RLS policies for orders - store managers can only see orders from their store
        await conn.execute(f"DROP POLICY IF EXISTS store_manager_orders ON {SCHEMA_NAME}.orders")
        await conn.execute(f"""
            CREATE POLICY store_manager_orders ON {SCHEMA_NAME}.orders
            FOR ALL TO PUBLIC
            USING (
                -- Super manager has access to all rows
                current_setting('app.current_rls_user_id', true) = '{SUPER_MANAGER_UUID}'
                OR
                -- Store managers can only see orders from their store
                EXISTS (
                    SELECT 1 FROM {SCHEMA_NAME}.stores s 
                    WHERE s.store_id = {SCHEMA_NAME}.orders.store_id 
                    AND s.rls_user_id::text = current_setting('app.current_rls_user_id', true)
                )
            )
        """)
        
        # Create RLS policies for order_items - direct store access for better performance
        await conn.execute(f"DROP POLICY IF EXISTS store_manager_order_items ON {SCHEMA_NAME}.order_items")
        await conn.execute(f"""
            CREATE POLICY store_manager_order_items ON {SCHEMA_NAME}.order_items
            FOR ALL TO PUBLIC
            USING (
                -- Super manager has access to all rows
                current_setting('app.current_rls_user_id', true) = '{SUPER_MANAGER_UUID}'
                OR
                -- Store managers can only see order items from their store
                EXISTS (
                    SELECT 1 FROM {SCHEMA_NAME}.stores s 
                    WHERE s.store_id = {SCHEMA_NAME}.order_items.store_id 
                    AND s.rls_user_id::text = current_setting('app.current_rls_user_id', true)
                )
            )
        """)
        
        # Create RLS policies for inventory - store managers can only see their store's inventory
        await conn.execute(f"DROP POLICY IF EXISTS store_manager_inventory ON {SCHEMA_NAME}.inventory")
        await conn.execute(f"""
            CREATE POLICY store_manager_inventory ON {SCHEMA_NAME}.inventory
            FOR ALL TO PUBLIC
            USING (
                -- Super manager has access to all rows
                current_setting('app.current_rls_user_id', true) = '{SUPER_MANAGER_UUID}'
                OR
                -- Store managers can only see their store's inventory
                EXISTS (
                    SELECT 1 FROM {SCHEMA_NAME}.stores s 
                    WHERE s.store_id = {SCHEMA_NAME}.inventory.store_id 
                    AND s.rls_user_id::text = current_setting('app.current_rls_user_id', true)
                )
            )
        """)
        
        # For customers, they can only see customers assigned to their store
        await conn.execute(f"DROP POLICY IF EXISTS store_manager_customers ON {SCHEMA_NAME}.customers")
        await conn.execute(f"""
            CREATE POLICY store_manager_customers ON {SCHEMA_NAME}.customers
            FOR ALL TO PUBLIC
            USING (
                -- Super manager has access to all rows
                current_setting('app.current_rls_user_id', true) = '{SUPER_MANAGER_UUID}'
                OR
                -- Store managers can only see customers assigned to their store
                EXISTS (
                    SELECT 1 FROM {SCHEMA_NAME}.stores s 
                    WHERE s.store_id = {SCHEMA_NAME}.customers.primary_store_id 
                    AND s.rls_user_id::text = current_setting('app.current_rls_user_id', true)
                )
                OR
                -- Also allow access to customers who have ordered from their store (backward compatibility)
                EXISTS (
                    SELECT 1 FROM {SCHEMA_NAME}.orders o
                    JOIN {SCHEMA_NAME}.stores s ON o.store_id = s.store_id
                    WHERE o.customer_id = {SCHEMA_NAME}.customers.customer_id
                    AND s.rls_user_id::text = current_setting('app.current_rls_user_id', true)
                )
            )
        """)
        
        # Create permissive RLS policies for reference tables that all authenticated users should access
        
        # Stores table - managers can see all stores (needed for reference)
        await conn.execute(f"DROP POLICY IF EXISTS all_users_stores ON {SCHEMA_NAME}.stores")
        await conn.execute(f"""
            CREATE POLICY all_users_stores ON {SCHEMA_NAME}.stores
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Categories table - all users can see all categories
        await conn.execute(f"DROP POLICY IF EXISTS all_users_categories ON {SCHEMA_NAME}.categories")
        await conn.execute(f"""
            CREATE POLICY all_users_categories ON {SCHEMA_NAME}.categories
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Product types table - all users can see all product types
        await conn.execute(f"DROP POLICY IF EXISTS all_users_product_types ON {SCHEMA_NAME}.product_types")
        await conn.execute(f"""
            CREATE POLICY all_users_product_types ON {SCHEMA_NAME}.product_types
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Suppliers table - all users can see all suppliers
        await conn.execute(f"DROP POLICY IF EXISTS all_users_suppliers ON {SCHEMA_NAME}.suppliers")
        await conn.execute(f"""
            CREATE POLICY all_users_suppliers ON {SCHEMA_NAME}.suppliers
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Products table - all users can see all products
        await conn.execute(f"DROP POLICY IF EXISTS all_users_products ON {SCHEMA_NAME}.products")
        await conn.execute(f"""
            CREATE POLICY all_users_products ON {SCHEMA_NAME}.products
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Product embeddings tables - all users can see all embeddings
        await conn.execute(f"DROP POLICY IF EXISTS all_users_product_image_embeddings ON {SCHEMA_NAME}.product_image_embeddings")
        await conn.execute(f"""
            CREATE POLICY all_users_product_image_embeddings ON {SCHEMA_NAME}.product_image_embeddings
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        await conn.execute(f"DROP POLICY IF EXISTS all_users_product_description_embeddings ON {SCHEMA_NAME}.product_description_embeddings")
        await conn.execute(f"""
            CREATE POLICY all_users_product_description_embeddings ON {SCHEMA_NAME}.product_description_embeddings
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Supplier performance table - all users can see all performance data
        await conn.execute(f"DROP POLICY IF EXISTS all_users_supplier_performance ON {SCHEMA_NAME}.supplier_performance")
        await conn.execute(f"""
            CREATE POLICY all_users_supplier_performance ON {SCHEMA_NAME}.supplier_performance
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        # Procurement requests table - all users can see all requests
        await conn.execute(f"DROP POLICY IF EXISTS all_users_procurement_requests ON {SCHEMA_NAME}.procurement_requests")
        await conn.execute(f"""
            CREATE POLICY all_users_procurement_requests ON {SCHEMA_NAME}.procurement_requests
            FOR ALL TO PUBLIC
            USING (true)
        """)
        
        logging.info("Row Level Security policies created successfully!")
        
    except Exception as e:
        logging.error(f"Error setting up Row Level Security policies: {e}")
        raise

async def setup_store_manager_permissions(conn):
    """Setup permissions for store_manager user to access the retail schema and tables"""
    try:
        logging.info("Setting up store_manager permissions...")
        
        # Check if store_manager role exists, create if it doesn't
        role_exists = await conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname = 'store_manager'"
        )
        
        if not role_exists:
            await conn.execute("CREATE ROLE store_manager LOGIN")
            logging.info("Created store_manager role")
        else:
            logging.info("store_manager role already exists")
        
        # Grant usage on the retail schema
        await conn.execute(f"GRANT USAGE ON SCHEMA {SCHEMA_NAME} TO store_manager")
        
        # Grant SELECT permissions on all tables in the retail schema
        await conn.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA {SCHEMA_NAME} TO store_manager")
        
        # Grant permissions on sequences (for SERIAL columns)
        await conn.execute(f"GRANT USAGE ON ALL SEQUENCES IN SCHEMA {SCHEMA_NAME} TO store_manager")
        
        # Grant permissions for future tables (in case new tables are added)
        await conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA_NAME} GRANT SELECT ON TABLES TO store_manager")
        await conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA {SCHEMA_NAME} GRANT USAGE ON SEQUENCES TO store_manager")
        
        # Do not grant INSERT, UPDATE, DELETE permissions to store_manager (SELECT only)
        
        logging.info("Store manager permissions granted successfully!")
        logging.info("Store manager can now:")
        logging.info("  - Access the retail schema")
        logging.info("  - SELECT, INSERT, UPDATE, DELETE on all tables")
        logging.info("  - Row Level Security policies will filter data based on rls_user_id")
        
    except Exception as e:
        logging.error(f"Error setting up store_manager permissions: {e}")
        raise

async def create_supplier_views(conn):
    """Create database views for supplier queries to optimize performance"""
    try:
        logging.info("Creating supplier database views...")
        
        # View 1: vw_suppliers_for_request
        view1_sql = f"""
        CREATE OR REPLACE VIEW {SCHEMA_NAME}.vw_suppliers_for_request AS
        SELECT DISTINCT
            s.supplier_id,
            s.supplier_name,
            s.supplier_code,
            s.contact_email,
            s.contact_phone,
            s.supplier_rating,
            s.esg_compliant,
            s.preferred_vendor,
            s.approved_vendor,
            s.lead_time_days,
            s.minimum_order_amount,
            s.bulk_discount_threshold,
            s.bulk_discount_percent,
            s.payment_terms,
            COUNT(p.product_id) as available_products,
            COALESCE(AVG(sp.overall_score), s.supplier_rating) as avg_performance_score,
            sc.contract_status,
            sc.contract_number,
            c.category_name
        FROM {SCHEMA_NAME}.suppliers s
        LEFT JOIN {SCHEMA_NAME}.products p ON s.supplier_id = p.supplier_id
        LEFT JOIN {SCHEMA_NAME}.categories c ON p.category_id = c.category_id
        LEFT JOIN {SCHEMA_NAME}.supplier_performance sp ON s.supplier_id = sp.supplier_id
            AND sp.evaluation_date >= CURRENT_DATE - INTERVAL '6 months'
        LEFT JOIN {SCHEMA_NAME}.supplier_contracts sc ON s.supplier_id = sc.supplier_id
            AND sc.contract_status = 'active'
        WHERE s.active_status = true
            AND s.approved_vendor = true
        GROUP BY s.supplier_id, s.supplier_name, s.supplier_code, s.contact_email,
                 s.contact_phone, s.supplier_rating, s.esg_compliant, s.preferred_vendor,
                 s.approved_vendor, s.lead_time_days, s.minimum_order_amount,
                 s.bulk_discount_threshold, s.bulk_discount_percent, s.payment_terms,
                 sc.contract_status, sc.contract_number, c.category_name;
        """
        
        await conn.execute(view1_sql)
        logging.info("✅ Created view: vw_suppliers_for_request")
        
        # View 2: vw_supplier_history_performance
        view2_sql = f"""
        CREATE OR REPLACE VIEW {SCHEMA_NAME}.vw_supplier_history_performance AS
        SELECT 
            s.supplier_id,
            s.supplier_name,
            s.supplier_code,
            s.supplier_rating,
            s.esg_compliant,
            s.preferred_vendor,
            s.lead_time_days,
            s.created_at as supplier_since,
            -- Performance metrics
            sp.evaluation_date,
            sp.cost_score,
            sp.quality_score,
            sp.delivery_score,
            sp.compliance_score,
            sp.overall_score,
            sp.notes as performance_notes,
            -- Recent procurement activity
            COUNT(pr.request_id) OVER (PARTITION BY s.supplier_id) as total_requests,
            SUM(pr.total_cost) OVER (PARTITION BY s.supplier_id) as total_value
        FROM {SCHEMA_NAME}.suppliers s
        LEFT JOIN {SCHEMA_NAME}.supplier_performance sp ON s.supplier_id = sp.supplier_id
        LEFT JOIN {SCHEMA_NAME}.procurement_requests pr ON s.supplier_id = pr.supplier_id;
        """
        
        await conn.execute(view2_sql)
        logging.info("✅ Created view: vw_supplier_history_performance")
        
        # View 3: vw_supplier_contract_details
        view3_sql = f"""
        CREATE OR REPLACE VIEW {SCHEMA_NAME}.vw_supplier_contract_details AS
        SELECT 
            s.supplier_id,
            s.supplier_name,
            s.supplier_code,
            s.contact_email,
            s.contact_phone,
            -- Contract details
            sc.contract_id,
            sc.contract_number,
            sc.contract_status,
            sc.start_date,
            sc.end_date,
            sc.contract_value,
            sc.payment_terms,
            sc.auto_renew,
            sc.created_at as contract_created,
            -- Calculated fields
            CASE 
                WHEN sc.end_date IS NOT NULL 
                THEN sc.end_date - CURRENT_DATE 
                ELSE NULL 
            END as days_until_expiry,
            CASE 
                WHEN sc.end_date IS NOT NULL AND sc.end_date <= CURRENT_DATE + INTERVAL '90 days'
                THEN true 
                ELSE false 
            END as renewal_due_soon
        FROM {SCHEMA_NAME}.suppliers s
        LEFT JOIN {SCHEMA_NAME}.supplier_contracts sc ON s.supplier_id = sc.supplier_id
        WHERE (sc.contract_status = 'active' OR sc.contract_status IS NULL);
        """
        
        await conn.execute(view3_sql)
        logging.info("✅ Created view: vw_supplier_contract_details")
        
        # View 4: vw_company_supplier_policies
        view4_sql = f"""
        CREATE OR REPLACE VIEW {SCHEMA_NAME}.vw_company_supplier_policies AS
        SELECT 
            policy_id,
            policy_name,
            policy_type,
            policy_content,
            department,
            minimum_order_threshold,
            approval_required,
            is_active,
            -- Additional context
            CASE 
                WHEN policy_type = 'procurement' THEN 'Covers supplier selection and procurement processes'
                WHEN policy_type = 'vendor_approval' THEN 'Defines vendor approval and onboarding requirements'
                WHEN policy_type = 'budget_authorization' THEN 'Specifies budget limits and authorization levels'
                WHEN policy_type = 'order_processing' THEN 'Outlines order processing and fulfillment procedures'
                ELSE 'General company policy'
            END as policy_description,
            LENGTH(policy_content) as content_length
        FROM {SCHEMA_NAME}.company_policies
        WHERE is_active = true;
        """
        
        await conn.execute(view4_sql)
        logging.info("✅ Created view: vw_company_supplier_policies")
        
        # Verify views were created
        verify_sql = f"""
        SELECT schemaname, viewname 
        FROM pg_views 
        WHERE schemaname = '{SCHEMA_NAME}' 
        AND viewname LIKE 'vw_%supplier%'
        ORDER BY viewname;
        """
        
        rows = await conn.fetch(verify_sql)
        logging.info("✅ Created supplier views:")
        for row in rows:
            logging.info(f"   - {row['schemaname']}.{row['viewname']}")
            
    except Exception as e:
        logging.error(f"Error creating supplier views: {e}")
        raise

async def batch_insert(conn, query: str, data: List[Tuple], batch_size: int = 1000):
    """Insert data in batches using asyncio"""
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        await conn.executemany(query, batch)

async def insert_customers(conn, num_customers: int = 100000):
    """Insert customer data into the database"""
    try:
        logging.info(f"Generating {num_customers:,} customers...")
        
        # Get store IDs for assignment
        store_rows = await conn.fetch(f"SELECT store_id, store_name FROM {SCHEMA_NAME}.stores")
        store_ids = [row['store_id'] for row in store_rows]
        
        if not store_ids:
            raise Exception("No stores found! Please insert stores first.")
        
        customers_data = []
        
        for i in range(1, num_customers + 1):
            first_name = fake.first_name().replace("'", "''")  # Escape single quotes
            last_name = fake.last_name().replace("'", "''")
            email = f"{first_name.lower()}.{last_name.lower()}.{i}@example.com"
            phone = generate_phone_number()
            
            # Assign every customer to a store based on weighted distribution
            # Use the same weighted store choice as orders for consistency
            preferred_store_name = weighted_store_choice()
            primary_store_id = None
            for row in store_rows:
                if row['store_name'] == preferred_store_name:
                    primary_store_id = row['store_id']
                    break
            
            # Fallback to first store if lookup fails (should not happen)
            if primary_store_id is None:
                primary_store_id = store_rows[0]['store_id']
            
            customers_data.append((first_name, last_name, email, phone, primary_store_id))
        
        await batch_insert(conn, f"INSERT INTO {SCHEMA_NAME}.customers (first_name, last_name, email, phone, primary_store_id) VALUES ($1, $2, $3, $4, $5)", customers_data)
        
        # Log customer distribution by store
        distribution = await conn.fetch(f"""
            SELECT s.store_name, COUNT(c.customer_id) as customer_count,
                   ROUND(100.0 * COUNT(c.customer_id) / {num_customers}, 1) as percentage
            FROM {SCHEMA_NAME}.stores s
            LEFT JOIN {SCHEMA_NAME}.customers c ON s.store_id = c.primary_store_id
            GROUP BY s.store_id, s.store_name
            ORDER BY customer_count DESC
        """)
        
        no_store_count = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.customers WHERE primary_store_id IS NULL")
        
        logging.info("Customer distribution by store:")
        for row in distribution:
            logging.info(f"  {row['store_name']}: {row['customer_count']:,} customers ({row['percentage']}%)")
        if no_store_count > 0:
            logging.info(f"  No primary store: {no_store_count:,} customers ({100.0 * no_store_count / num_customers:.1f}%)")
        else:
            logging.info("  ✅ All customers have been assigned to stores!")
        
        logging.info(f"Successfully inserted {num_customers:,} customers!")
    except Exception as e:
        logging.error(f"Error inserting customers: {e}")
        raise

async def insert_stores(conn):
    """Insert store data into the database"""
    try:
        logging.info("Generating stores...")
        
        stores_data = []
        
        for store_key, store_config in stores.items():
            # Get the actual store name
            if is_using_store_ids():
                store_name = store_config.get('store_name', store_key)
            else:
                store_name = store_key
            
            # Determine if this is an online store
            is_online = "online" in store_name.lower()
            # Get the fixed UUID from the reference data
            rls_user_id = store_config.get('rls_user_id')
            if not rls_user_id:
                raise ValueError(f"No rls_user_id found for store: {store_name}")
            stores_data.append((store_name, rls_user_id, is_online))
        
        await batch_insert(conn, f"INSERT INTO {SCHEMA_NAME}.stores (store_name, rls_user_id, is_online) VALUES ($1, $2, $3)", stores_data)
        
        # Log the manager IDs for workshop purposes
        rows = await conn.fetch(f"SELECT store_name, rls_user_id FROM {SCHEMA_NAME}.stores ORDER BY store_name")
        logging.info("Store Manager IDs (for workshop use):")
        for row in rows:
            logging.info(f"  {row['store_name']}: {row['rls_user_id']}")
        
        logging.info(f"Successfully inserted {len(stores_data):,} stores!")
    except Exception as e:
        logging.error(f"Error inserting stores: {e}")
        raise

async def insert_categories(conn):
    """Insert category data into the database"""
    try:
        logging.info("Generating categories...")
        
        categories_data = []
        
        # Extract unique categories from product data
        for main_category in main_categories.keys():
            categories_data.append((main_category,))
        
        await batch_insert(conn, f"INSERT INTO {SCHEMA_NAME}.categories (category_name) VALUES ($1)", categories_data)
        
        logging.info(f"Successfully inserted {len(categories_data):,} categories!")
    except Exception as e:
        logging.error(f"Error inserting categories: {e}")
        raise

async def insert_product_types(conn):
    """Insert product type data into the database"""
    try:
        logging.info("Generating product types...")
        
        product_types_data = []
        
        # Get category_id mapping
        category_mapping = {}
        rows = await conn.fetch(f"SELECT category_id, category_name FROM {SCHEMA_NAME}.categories")
        for row in rows:
            category_mapping[row['category_name']] = row['category_id']
        
        # Extract product types for each category
        for main_category, subcategories in main_categories.items():
            category_id = category_mapping[main_category]
            for subcategory in subcategories.keys():
                product_types_data.append((category_id, subcategory))
        
        await batch_insert(conn, f"INSERT INTO {SCHEMA_NAME}.product_types (category_id, type_name) VALUES ($1, $2)", product_types_data)
        
        logging.info(f"Successfully inserted {len(product_types_data):,} product types!")
    except Exception as e:
        logging.error(f"Error inserting product types: {e}")
        raise

async def insert_suppliers(conn):
    """Insert supplier data into the database from JSON file"""
    try:
        logging.info(f"Loading suppliers from {SUPPLIER_DATA_FILE}...")
        
        # Load supplier data from JSON file
        supplier_json_path = os.path.join(os.path.dirname(__file__), REFERENCE_DATA_DIR, SUPPLIER_DATA_FILE)
        
        if not os.path.exists(supplier_json_path):
            raise FileNotFoundError(f"Supplier data file not found: {supplier_json_path}")
        
        with open(supplier_json_path, 'r') as f:
            supplier_config = json.load(f)
        
        # Handle both array format and object format
        if 'suppliers' in supplier_config:
            suppliers_from_json = supplier_config['suppliers']
        else:
            # Suppliers are direct properties with numeric keys
            suppliers_from_json = [supplier_config[key] for key in supplier_config.keys() if key.isdigit()]
        
        if not suppliers_from_json:
            raise ValueError(f"No suppliers found in {SUPPLIER_DATA_FILE}")
        
        logging.info(f"Loaded {len(suppliers_from_json)} suppliers from JSON file")
        
        # Transform JSON data into database format
        supplier_insert_data = []
        for idx, supplier in enumerate(suppliers_from_json, 1):
            # Use supplier code from JSON if provided, otherwise generate
            supplier_code = supplier.get('supplier_code', f"SUP{idx:03d}")
            
            # Parse address (assuming single address string, split into components)
            address = supplier.get('address', '')
            address_parts = address.split(',') if address else []
            
            # Extract components safely
            address_line1 = address_parts[0].strip() if len(address_parts) > 0 else ''
            city = address_parts[1].strip() if len(address_parts) > 1 else 'Seattle'
            
            # Handle state/postal code more robustly
            if len(address_parts) > 2:
                state_postal = address_parts[2].strip().split()
                state = state_postal[0] if len(state_postal) > 0 else 'WA'
                postal_code = state_postal[1] if len(state_postal) > 1 else '98000'
            else:
                state = 'WA'
                postal_code = '98000'
            
            # Calculate bulk discount threshold and percentage
            min_order = supplier.get('min_order_amount', 500.00)
            bulk_threshold = min_order * 5  # Bulk discounts at 5x minimum order
            bulk_discount = random.uniform(5.0, 10.0)  # 5-10% bulk discount
            
            # Get rating from JSON, or use default
            rating = supplier.get('rating', 4.0)
            
            # Get ESG compliance from JSON, with fallback logic
            esg_compliant = supplier.get('esg_compliant', rating >= 4.0)
            
            # Get preferred vendor status from JSON, with fallback logic
            is_preferred = supplier.get('preferred_vendor', rating >= 4.5)
            
            # Get approved vendor status from JSON, with fallback logic
            approved_vendor = supplier.get('approved_vendor', rating >= 3.5)
            
            # Use supplier_id from JSON if provided, otherwise use auto-increment
            supplier_id = supplier.get('supplier_id', idx)
            
            # Get payment terms from contract if available, otherwise from supplier
            payment_terms = supplier.get('payment_terms', 'Net 30')
            if 'contracts' in supplier and len(supplier['contracts']) > 0:
                payment_terms = supplier['contracts'][0].get('payment_terms', payment_terms)
            
            supplier_insert_data.append((
                supplier_id,
                supplier.get('supplier_name', supplier.get('name', f'Supplier {idx}')),
                supplier_code,
                supplier.get('contact_email', supplier.get('email', f'contact{idx}@supplier.com')),
                supplier.get('contact_phone', supplier.get('phone', f'(555) {idx:03d}-0000')),
                address_line1,
                '',  # address_line2
                city,
                state,
                postal_code,
                'USA',
                payment_terms,
                supplier.get('lead_time_days', 14),
                min_order,
                bulk_threshold,
                bulk_discount,
                rating,
                esg_compliant,
                approved_vendor,
                is_preferred
            ))
        
        logging.info(f"Prepared {len(supplier_insert_data)} suppliers for insertion...")
        
        # Insert supplier data
        await batch_insert(conn, f"""
            INSERT INTO {SCHEMA_NAME}.suppliers (
                supplier_id, supplier_name, supplier_code, contact_email, contact_phone,
                address_line1, address_line2, city, state_province, postal_code, country,
                payment_terms, lead_time_days, minimum_order_amount, bulk_discount_threshold, bulk_discount_percent,
                supplier_rating, esg_compliant, approved_vendor, preferred_vendor
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)
        """, supplier_insert_data)
        
        logging.info(f"Successfully inserted {len(supplier_insert_data):,} suppliers!")
        
        # Store category and product type mappings for later use
        global SUPPLIER_CATEGORY_MAP
        SUPPLIER_CATEGORY_MAP = {}
        for supplier in suppliers_from_json:
            supplier_name = supplier.get('name', '')
            categories = supplier.get('categories', [])
            product_types = supplier.get('product_types', [])
            
            for category in categories:
                if category not in SUPPLIER_CATEGORY_MAP:
                    SUPPLIER_CATEGORY_MAP[category] = []
                SUPPLIER_CATEGORY_MAP[category].append(supplier_name)
            
            for product_type in product_types:
                product_key = f"product_type:{product_type}"
                if product_key not in SUPPLIER_CATEGORY_MAP:
                    SUPPLIER_CATEGORY_MAP[product_key] = []
                SUPPLIER_CATEGORY_MAP[product_key].append(supplier_name)
        
        # Insert initial supplier performance data
        logging.info("Generating supplier performance evaluations...")
        
        # Get supplier IDs
        supplier_rows = await conn.fetch(f"SELECT supplier_id, supplier_name FROM {SCHEMA_NAME}.suppliers")
        
        performance_data = []
        for supplier in supplier_rows:
            supplier_id = supplier['supplier_id']
            # Generate 3-6 months of performance evaluations
            for months_ago in range(0, random.randint(3, 7)):
                evaluation_date = date.today().replace(day=1) - timedelta(days=months_ago * 30)
                
                # Generate realistic performance scores with some variation
                base_cost_score = random.uniform(3.5, 4.8)
                base_quality_score = random.uniform(3.2, 4.9)
                base_delivery_score = random.uniform(3.0, 4.7)
                base_compliance_score = random.uniform(4.2, 5.0)
                
                # Add some monthly variation
                cost_score = max(1.0, min(5.0, base_cost_score + random.uniform(-0.3, 0.3)))
                quality_score = max(1.0, min(5.0, base_quality_score + random.uniform(-0.4, 0.4)))
                delivery_score = max(1.0, min(5.0, base_delivery_score + random.uniform(-0.5, 0.5)))
                compliance_score = max(1.0, min(5.0, base_compliance_score + random.uniform(-0.2, 0.2)))
                
                # Calculate overall score as weighted average
                overall_score = (cost_score * 0.3 + quality_score * 0.3 + delivery_score * 0.25 + compliance_score * 0.15)
                
                performance_data.append((
                    supplier_id, evaluation_date, cost_score, quality_score, 
                    delivery_score, compliance_score, overall_score, 
                    f"Monthly evaluation for {supplier['supplier_name']}"
                ))
        
        await batch_insert(conn, f"""
            INSERT INTO {SCHEMA_NAME}.supplier_performance (
                supplier_id, evaluation_date, cost_score, quality_score,
                delivery_score, compliance_score, overall_score, notes
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, performance_data)
        
        logging.info(f"Successfully inserted {len(performance_data):,} supplier performance evaluations!")


        

        
    except Exception as e:
        logging.error(f"Error inserting suppliers: {e}")
        raise

async def insert_agent_support_data(conn):
    """Insert agent support data (approvers, contracts, policies, procurement requests, notifications)"""
    try:
        logging.info("Generating essential agent support data...")
        
        # Generate basic approvers for demonstration
        approvers_data = []
        departments = ["Finance", "Operations", "Procurement", "Management"]
        
        # Create simple approval hierarchy
        approver_configs = [
            ("EXEC001", "Jane CEO", "jane.ceo@company.com", "Management", 1000000),
            ("DIR001", "John Finance Director", "john.director@company.com", "Finance", 250000),
            ("DIR002", "Sarah Operations Director", "sarah.ops@company.com", "Operations", 200000),
            ("MGR001", "Mike Procurement Manager", "mike.proc@company.com", "Procurement", 50000),
            ("MGR002", "Lisa Finance Manager", "lisa.fin@company.com", "Finance", 25000),
            ("SUP001", "Tom Operations Supervisor", "tom.ops@company.com", "Operations", 10000),
            ("SUP002", "Amy Procurement Specialist", "amy.proc@company.com", "Procurement", 5000)
        ]
        
        for emp_id, name, email, dept, limit in approver_configs:
            approvers_data.append((emp_id, name, email, dept, limit, True))
        
        # Insert approvers
        await batch_insert(conn, f"""
            INSERT INTO {SCHEMA_NAME}.approvers (
                employee_id, full_name, email, department, approval_limit, is_active
            ) VALUES ($1, $2, $3, $4, $5, $6)
        """, approvers_data)
        
        # Generate simplified supplier contracts using data from JSON
        # Load supplier data to get contract values and end dates
        try:
            supplier_json_path = os.path.join(os.path.dirname(__file__), REFERENCE_DATA_DIR, SUPPLIER_DATA_FILE)
            with open(supplier_json_path, 'r') as f:
                supplier_config = json.load(f)
            suppliers_from_json = supplier_config.get('suppliers', [])
        except Exception as e:
            logging.warning(f"Failed to load supplier data for contracts: {e}")
            suppliers_from_json = []
        
        contract_data = []
        
        # Get actual supplier IDs from database to match with JSON data
        supplier_rows = await conn.fetch(f"SELECT supplier_id, supplier_name FROM {SCHEMA_NAME}.suppliers ORDER BY supplier_id")
        
        for i, supplier_row in enumerate(supplier_rows, 1):
            supplier_id = supplier_row['supplier_id']
            
            # Find matching supplier in JSON data
            json_supplier = None
            if i <= len(suppliers_from_json):
                json_supplier = suppliers_from_json[i-1]  # JSON is 0-indexed, supplier_id is 1-indexed
            
            # Use JSON data if available, otherwise fallback to defaults
            if json_supplier and 'contract_value' in json_supplier and 'contract_end_date' in json_supplier:
                contract_value = json_supplier['contract_value']
                end_date_str = json_supplier['contract_end_date']
                end_date = date.fromisoformat(end_date_str)
                payment_terms = json_supplier.get('payment_terms', 'Net 30')
                contract_number = json_supplier.get('contract_number', f"CON-2024-{i:03d}")
            else:
                # Fallback values
                contract_value = random.uniform(50000, 500000)
                end_date = date(2025, 12, 31)
                payment_terms = random.choice(["Net 30", "Net 45", "Net 60"])
                contract_number = f"CON-2024-{i:03d}"
            
            contract_data.append((
                supplier_id,
                contract_number,
                "active",
                date(2024, 1, 1),
                end_date,
                contract_value,
                payment_terms,
                random.choice([True, False])
            ))
        
        await batch_insert(conn, f"""
            INSERT INTO {SCHEMA_NAME}.supplier_contracts (
                supplier_id, contract_number, contract_status, start_date, end_date,
                contract_value, payment_terms, auto_renew
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, contract_data)
        
        # Generate essential company policies
        policy_data = [
            ("Procurement Policy", "procurement", "All purchases over $5,000 require manager approval. Competitive bidding required for orders over $25,000.", "Procurement", 5000, True),
            ("Order Processing Policy", "order_processing", "Orders processed within 24 hours. Rush orders require $50 fee and manager approval.", "Operations", None, False),
            ("Budget Authorization", "budget_authorization", "Spending limits: Manager $50K, Director $250K, Executive $1M+", "Finance", None, True),
            ("Vendor Approval", "vendor_approval", "All new vendors require approval and background check completion.", "Procurement", None, True)
        ]
        
        await batch_insert(conn, f"""
            INSERT INTO {SCHEMA_NAME}.company_policies (
                policy_name, policy_type, policy_content, department, minimum_order_threshold, approval_required
            ) VALUES ($1, $2, $3, $4, $5, $6)
        """, policy_data)
        
        # Generate sample procurement requests (now products table exists)
        procurement_data = []
        product_rows = await conn.fetch(f"SELECT product_id, supplier_id, cost FROM {SCHEMA_NAME}.products LIMIT 20")
        departments = ["Operations", "Finance", "Procurement", "Management"]
        urgency_levels = ["Low", "Normal", "High", "Critical"]
        approval_statuses = ["Pending", "Approved", "Rejected"]
        
        for i in range(25):  # Generate 25 sample procurement requests
            if not product_rows:
                break
            
            product = random.choice(product_rows)
            product_id = product['product_id'] 
            supplier_id = product['supplier_id']
            unit_cost = float(product['cost'])
            quantity_requested = random.randint(10, 100)
            total_cost = unit_cost * quantity_requested
            
            request_number = f"PR-2024-{i+1:04d}"
            requester_name = fake.name()
            requester_email = f"{requester_name.lower().replace(' ', '.')}@company.com" 
            department = random.choice(departments)
            urgency_level = random.choice(urgency_levels)
            approval_status = random.choices(approval_statuses, weights=[40, 50, 10], k=1)[0]
            
            request_date = date.today() - timedelta(days=random.randint(1, 60))
            required_by_date = request_date + timedelta(days=random.randint(7, 30))
            justification = fake.sentence()
            
            approved_by = None
            approved_at = None
            if approval_status == "Approved":
                approved_by = random.choice([a[1] for a in approvers_data])  # Pick random approver name
                approved_at = request_date + timedelta(days=random.randint(1, 5))
            
            procurement_data.append((
                request_number, requester_name, requester_email, department,
                product_id, supplier_id, quantity_requested, unit_cost, total_cost,
                justification, urgency_level, approval_status, approved_by, approved_at,
                request_date, required_by_date
            ))
        
        if procurement_data:
            await batch_insert(conn, f"""
                INSERT INTO {SCHEMA_NAME}.procurement_requests (
                    request_number, requester_name, requester_email, department,
                    product_id, supplier_id, quantity_requested, unit_cost, total_cost,
                    justification, urgency_level, approval_status, approved_by, approved_at,
                    request_date, required_by_date
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16)
            """, procurement_data)

        # Generate sample notifications
        notification_data = []
        recent_requests = await conn.fetch(f"""
            SELECT request_id, requester_email, total_cost, approval_status 
            FROM {SCHEMA_NAME}.procurement_requests 
            ORDER BY request_date DESC LIMIT 10
        """)
        
        for req in recent_requests:
            # Find appropriate approver
            suitable_approver = next((a for a in approvers_data if a[4] >= req['total_cost']), approvers_data[0])
            
            notification_data.append((
                req['request_id'],
                "approval_request",
                suitable_approver[2],  # email
                f"Approval Required: Request #{req['request_id']}",
                f"Please review procurement request for ${req['total_cost']:,.2f}"
            ))
        
        if notification_data:
            await batch_insert(conn, f"""
                INSERT INTO {SCHEMA_NAME}.notifications (
                    request_id, notification_type, recipient_email, subject, message
                ) VALUES ($1, $2, $3, $4, $5)
            """, notification_data)
        
        logging.info(f"Successfully inserted {len(approvers_data)} approvers!")
        logging.info(f"Successfully inserted {len(contract_data)} supplier contracts!")
        logging.info(f"Successfully inserted {len(policy_data)} company policies!")
        logging.info(f"Successfully inserted {len(procurement_data)} procurement requests!")
        logging.info(f"Successfully inserted {len(notification_data)} notifications!")
        
    except Exception as e:
        logging.error(f"Error inserting agent support data: {e}")
        raise

async def insert_products(conn):
    """Insert product data into the database"""
    try:
        logging.info("Generating products...")
        
        # Get category and type mappings
        category_mapping = {}
        rows = await conn.fetch(f"SELECT category_id, category_name FROM {SCHEMA_NAME}.categories")
        for row in rows:
            category_mapping[row['category_name']] = row['category_id']
        
        type_mapping = {}
        rows = await conn.fetch(f"SELECT type_id, type_name, category_id FROM {SCHEMA_NAME}.product_types")
        for row in rows:
            type_mapping[(row['category_id'], row['type_name'])] = row['type_id']
        
        # Get supplier mappings - assign suppliers to product categories
        supplier_rows = await conn.fetch(f"SELECT supplier_id, supplier_name, preferred_vendor FROM {SCHEMA_NAME}.suppliers ORDER BY preferred_vendor DESC, supplier_rating DESC")
        
        if not supplier_rows:
            raise Exception("No suppliers found! Please insert suppliers first.")
        
        # Use the SUPPLIER_CATEGORY_MAP created during supplier insertion
        # This mapping was built from the supplier data file's categories and product_types
        category_supplier_mapping = {}
        
        # Create a dict for quick supplier lookup by name
        supplier_by_name = {s['supplier_name']: s for s in supplier_rows}
        
        # Build category mapping from SUPPLIER_CATEGORY_MAP
        for category, supplier_names in SUPPLIER_CATEGORY_MAP.items():
            if not category.startswith('product_type:'):  # Only process category entries
                category_supplier_mapping[category] = [
                    supplier_by_name[name] for name in supplier_names if name in supplier_by_name
                ]
        
        # Default suppliers for any unmapped categories
        default_suppliers = supplier_rows[:5]  # Use top 5 suppliers as default
        
        products_data = []
        
        for main_category, subcategories in main_categories.items():
            category_id = category_mapping[main_category]
            
            # Get appropriate suppliers for this category
            category_suppliers = category_supplier_mapping.get(main_category, default_suppliers)
            if not category_suppliers:
                category_suppliers = default_suppliers
            
            for subcategory, product_list in subcategories.items():
                if not product_list:  # Handle empty product lists
                    continue
                
                type_id = type_mapping.get((category_id, subcategory))
                if not type_id:
                    logging.warning(f"Type ID not found for category {main_category}, type {subcategory}")
                    continue
                    
                for product_details in product_list:
                    product_name = product_details["name"]
                    sku = product_details.get("sku", f"SKU{len(products_data)+1:06d}")  # Fallback if no SKU
                    json_price = product_details["price"]
                    description = product_details["description"]
                    
                    # Assign supplier - prefer preferred vendors, with some randomization
                    supplier = random.choices(
                        category_suppliers, 
                        weights=[3 if s['preferred_vendor'] else 1 for s in category_suppliers], 
                        k=1
                    )[0]
                    supplier_id = supplier['supplier_id']
                    
                    # Treat the JSON price as the actual store selling price
                    base_price = float(json_price)
                    
                    # Calculate cost for 33% gross margin
                    # Gross Margin = (Selling Price - Cost) / Selling Price = 0.33
                    # Therefore: Cost = Selling Price × (1 - 0.33) = Selling Price × 0.67
                    cost = round(base_price * 0.67, 2)
                    
                    # Set procurement lead time based on supplier
                    # Get supplier info for lead time
                    supplier_info = await conn.fetchrow(f"SELECT lead_time_days FROM {SCHEMA_NAME}.suppliers WHERE supplier_id = $1", supplier_id)
                    procurement_lead_time = supplier_info['lead_time_days'] if supplier_info else 14
                    
                    # Set minimum order quantity (vary by product type)
                    min_order_qty = random.choices([1, 5, 10, 25], weights=[60, 25, 10, 5], k=1)[0]
                    
                    products_data.append((sku, product_name, category_id, type_id, supplier_id, cost, base_price, description, procurement_lead_time, min_order_qty))
        
        await batch_insert(conn, f"""
            INSERT INTO {SCHEMA_NAME}.products 
            (sku, product_name, category_id, type_id, supplier_id, cost, base_price, product_description, procurement_lead_time_days, minimum_order_quantity) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """, products_data)
        
        logging.info(f"Successfully inserted {len(products_data):,} products!")
        return len(products_data)  # Return the number of products inserted
    except Exception as e:
        logging.error(f"Error inserting products: {e}")
        raise

def get_store_multipliers(store_name):
    """Get order frequency multipliers based on store name"""
    store_data = stores.get(store_name, {
        'customer_distribution_weight': 1,
        'order_frequency_multiplier': 1.0, 
        'order_value_multiplier': 1.0
    })
    return {'orders': store_data.get('order_frequency_multiplier', 1.0)}

def get_yearly_weight(year):
    """Get the weight for each year to create growth pattern"""
    # Map years to the array indices
    year_mapping = {2021: 0, 2022: 1, 2023: 2, 2024: 3, 2025: 4}
    if 'year_weights' in reference_data and year in year_mapping:
        return reference_data['year_weights'][year_mapping[year]]
    return 1.0  # Default weight

def weighted_year_choice():
    """Choose a year based on growth pattern weights"""
    years = [2021, 2022, 2023, 2024, 2025]  # Match the years we have weights for
    weights = [get_yearly_weight(year) for year in years]
    return random.choices(years, weights=weights, k=1)[0]

async def get_store_id_by_name(conn, store_name):
    """Get store_id for a given store name"""
    row = await conn.fetchrow(f"SELECT store_id FROM {SCHEMA_NAME}.stores WHERE store_name = $1", store_name)
    return row['store_id'] if row else 1  # Default to store_id 1 if not found

def choose_seasonal_product_category(month, store_name=None):
    """Choose a category based on seasonal multipliers for the store's climate zone"""
    categories = []
    weights = []
    
    for category_name in main_categories.keys():
        # Get seasonal multipliers for this store and category
        seasonal_multipliers = get_seasonal_multipliers_for_store_and_category(store_name or "Zava Physical Store Seattle", category_name)
        # Use month index (0-11) to get the multiplier
        seasonal_weight = seasonal_multipliers[month - 1]  # month is 1-12, array is 0-11
        categories.append(category_name)
        weights.append(seasonal_weight)
    
    return random.choices(categories, weights=weights, k=1)[0]

def choose_product_type(main_category):
    """Choose a product type within a category with equal weights"""
    product_types = []
    for key in main_categories[main_category].keys():
        if isinstance(main_categories[main_category][key], list):
            product_types.append(key)
    
    if not product_types:
        logging.warning(f"No product types found for category: {main_category}")
        return None
    return random.choice(product_types)

def extract_products_with_embeddings(product_data: Dict) -> List[Tuple[str, str, List[float]]]:
    """
    Extract products with image embeddings from the JSON structure.
    
    Returns:
        List of tuples: (sku, image_path, image_embedding)
    """
    products_with_embeddings = []
    
    for category_name, category_data in product_data.get('main_categories', {}).items():
        for product_type, products in category_data.items():
            # Skip non-product keys like seasonal multipliers
            if not isinstance(products, list):
                continue
                
            for product in products:
                if isinstance(product, dict):
                    sku = product.get('sku')
                    image_path = product.get('image_path')
                    image_embedding = product.get('image_embedding')
                    
                    if sku and image_path and image_embedding:
                        products_with_embeddings.append((sku, image_path, image_embedding))
                    else:
                        logging.debug(f"Skipping product with missing data: SKU={sku}")
    
    logging.info(f"Found {len(products_with_embeddings)} products with embeddings")
    return products_with_embeddings

async def get_product_id_by_sku(conn: asyncpg.Connection, sku: str) -> Optional[int]:
    """Get product_id for a given SKU"""
    try:
        result = await conn.fetchval(
            f"SELECT product_id FROM {SCHEMA_NAME}.products WHERE sku = $1",
            sku
        )
        return result
    except Exception as e:
        logging.error(f"Error getting product_id for SKU {sku}: {e}")
        return None

async def insert_product_embedding(
    conn: asyncpg.Connection, 
    product_id: int, 
    image_path: str, 
    image_embedding: List[float]
) -> bool:
    """Insert a product embedding record"""
    try:
        # Store just the image filename without any path prefix
        image_url = os.path.basename(image_path)
        
        # Convert the embedding list to a vector string format
        embedding_str = f"[{','.join([str(x) for x in image_embedding])}]"
        
        await conn.execute(
            f"""
            INSERT INTO {SCHEMA_NAME}.product_image_embeddings 
            (product_id, image_url, image_embedding) 
            VALUES ($1, $2, $3::vector)
            """,
            product_id, image_url, embedding_str
        )
        return True
    except Exception as e:
        logging.error(f"Error inserting embedding for product_id {product_id}: {e}")
        return False

async def clear_existing_embeddings(conn: asyncpg.Connection) -> None:
    """Clear all existing product image embeddings"""
    try:
        result = await conn.execute(f"DELETE FROM {SCHEMA_NAME}.product_image_embeddings")
        logging.info(f"Cleared existing embeddings: {result}")
    except Exception as e:
        logging.error(f"Error clearing existing embeddings: {e}")
        raise

async def populate_product_image_embeddings(conn: asyncpg.Connection, clear_existing: bool = False, batch_size: int = 100) -> None:
    """Populate product image embeddings from product data file"""
    
    logging.info("Loading product data for embeddings...")
    products_with_embeddings = extract_products_with_embeddings(product_data)
    
    if not products_with_embeddings:
        logging.warning("No products with embeddings found in the data")
        return
    
    try:
        # Clear existing embeddings if requested
        if clear_existing:
            logging.info("Clearing existing product embeddings...")
            await clear_existing_embeddings(conn)
        
        # Process products in batches
        inserted_count = 0
        skipped_count = 0
        error_count = 0
        
        for i in range(0, len(products_with_embeddings), batch_size):
            batch = products_with_embeddings[i:i + batch_size]
            
            logging.info(f"Processing embeddings batch {i//batch_size + 1}/{(len(products_with_embeddings) + batch_size - 1)//batch_size}")
            
            for sku, image_path, image_embedding in batch:
                # Get product_id for this SKU
                product_id = await get_product_id_by_sku(conn, sku)
                
                if product_id is None:
                    logging.debug(f"Product not found for SKU: {sku}")
                    skipped_count += 1
                    continue
                
                # Insert the embedding
                if await insert_product_embedding(conn, product_id, image_path, image_embedding):
                    inserted_count += 1
                else:
                    error_count += 1
        
        # Summary
        logging.info("Product embeddings population complete!")
        logging.info(f"  Inserted: {inserted_count}")
        logging.info(f"  Skipped (product not found): {skipped_count}")
        logging.info(f"  Errors: {error_count}")
        logging.info(f"  Total processed: {len(products_with_embeddings)}")
        
    except Exception as e:
        logging.error(f"Error populating product embeddings: {e}")
        raise

async def verify_embeddings_table(conn: asyncpg.Connection) -> None:
    """Verify the product_image_embeddings table exists and show sample data"""
    try:
        # Check table existence
        table_exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = $1 AND table_name = 'product_image_embeddings'
            )
            """,
            SCHEMA_NAME
        )
        
        if not table_exists:
            logging.error(f"Table {SCHEMA_NAME}.product_image_embeddings does not exist!")
            return
        
        # Get row count
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.product_image_embeddings")
        if count is None:
            count = 0
        logging.info(f"Product image embeddings table has {count} records")
        
        # Show sample data
        if count > 0:
            sample = await conn.fetch(
                f"""
                SELECT pe.product_id, p.sku, p.product_name, pe.image_url,
                       vector_dims(pe.image_embedding) as embedding_dimension
                FROM {SCHEMA_NAME}.product_image_embeddings pe
                JOIN {SCHEMA_NAME}.products p ON pe.product_id = p.product_id
                LIMIT 5
                """
            )
            
            logging.info("Sample embeddings data:")
            for row in sample:
                logging.info(f"  Product ID: {row['product_id']}, SKU: {row['sku']}, "
                           f"Product: {row['product_name'][:50]}..., "
                           f"Embedding dim: {row['embedding_dimension']}")
        
    except Exception as e:
        logging.error(f"Error verifying embeddings table: {e}")

def extract_products_with_description_embeddings(product_data: Dict) -> List[Tuple[str, List[float]]]:
    """
    Extract products with description embeddings from the JSON structure.
    
    Returns:
        List of tuples: (sku, description_embedding)
    """
    products_with_description_embeddings = []
    
    for _category_name, category_data in product_data.get('main_categories', {}).items():
        for _product_type, products in category_data.items():
            # Skip non-product keys like seasonal multipliers
            if not isinstance(products, list):
                continue
                
            for product in products:
                if isinstance(product, dict):
                    sku = product.get('sku')
                    description_embedding = product.get('description_embedding')
                    
                    if sku and description_embedding:
                        products_with_description_embeddings.append((sku, description_embedding))
                    else:
                        logging.debug(f"Skipping product with missing description embedding: SKU={sku}")
    
    logging.info(f"Found {len(products_with_description_embeddings)} products with description embeddings")
    return products_with_description_embeddings

async def insert_product_description_embedding(
    conn: asyncpg.Connection, 
    product_id: int, 
    description_embedding: List[float]
) -> bool:
    """Insert a product description embedding record"""
    try:
        # Convert the embedding list to a vector string format
        embedding_str = f"[{','.join([str(x) for x in description_embedding])}]"
        
        await conn.execute(
            f"""
            INSERT INTO {SCHEMA_NAME}.product_description_embeddings 
            (product_id, description_embedding) 
            VALUES ($1, $2::vector)
            """,
            product_id, embedding_str
        )
        return True
    except Exception as e:
        logging.error(f"Error inserting description embedding for product_id {product_id}: {e}")
        return False

async def clear_existing_description_embeddings(conn: asyncpg.Connection) -> None:
    """Clear all existing product description embeddings"""
    try:
        result = await conn.execute(f"DELETE FROM {SCHEMA_NAME}.product_description_embeddings")
        logging.info(f"Cleared existing description embeddings: {result}")
    except Exception as e:
        logging.error(f"Error clearing existing description embeddings: {e}")
        raise

async def populate_product_description_embeddings(conn: asyncpg.Connection, clear_existing: bool = False, batch_size: int = 100) -> None:
    """Populate product description embeddings from product data file"""
    
    logging.info("Loading product data for description embeddings...")
    products_with_description_embeddings = extract_products_with_description_embeddings(product_data)
    
    if not products_with_description_embeddings:
        logging.warning("No products with description embeddings found in the data")
        return
    
    try:
        # Clear existing description embeddings if requested
        if clear_existing:
            logging.info("Clearing existing product description embeddings...")
            await clear_existing_description_embeddings(conn)
        
        # Process products in batches
        inserted_count = 0
        skipped_count = 0
        error_count = 0
        
        for i in range(0, len(products_with_description_embeddings), batch_size):
            batch = products_with_description_embeddings[i:i + batch_size]
            
            logging.info(f"Processing description embeddings batch {i//batch_size + 1}/{(len(products_with_description_embeddings) + batch_size - 1)//batch_size}")
            
            for sku, description_embedding in batch:
                # Get product_id for this SKU
                product_id = await get_product_id_by_sku(conn, sku)
                
                if product_id is None:
                    logging.debug(f"Product not found for SKU: {sku}")
                    skipped_count += 1
                    continue
                
                # Insert the description embedding
                if await insert_product_description_embedding(conn, product_id, description_embedding):
                    inserted_count += 1
                else:
                    error_count += 1
        
        # Summary
        logging.info("Product description embeddings population complete!")
        logging.info(f"  Inserted: {inserted_count}")
        logging.info(f"  Skipped (product not found): {skipped_count}")
        logging.info(f"  Errors: {error_count}")
        logging.info(f"  Total processed: {len(products_with_description_embeddings)}")
        
    except Exception as e:
        logging.error(f"Error populating product description embeddings: {e}")
        raise

async def verify_description_embeddings_table(conn: asyncpg.Connection) -> None:
    """Verify the product_description_embeddings table exists and show sample data"""
    try:
        # Check table existence
        table_exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = $1 AND table_name = 'product_description_embeddings'
            )
            """,
            SCHEMA_NAME
        )
        
        if not table_exists:
            logging.error(f"Table {SCHEMA_NAME}.product_description_embeddings does not exist!")
            return
        
        # Get row count
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.product_description_embeddings")
        if count is None:
            count = 0
        logging.info(f"Product description embeddings table has {count} records")
        
        # Show sample data
        if count > 0:
            sample = await conn.fetch(
                f"""
                SELECT pe.product_id, p.sku, p.product_name,
                       vector_dims(pe.description_embedding) as embedding_dimension
                FROM {SCHEMA_NAME}.product_description_embeddings pe
                JOIN {SCHEMA_NAME}.products p ON pe.product_id = p.product_id
                LIMIT 5
                """
            )
            
            logging.info("Sample description embeddings data:")
            for row in sample:
                logging.info(f"  Product ID: {row['product_id']}, SKU: {row['sku']}, "
                           f"Product: {row['product_name'][:50]}..., "
                           f"Embedding dim: {row['embedding_dimension']}")
        
    except Exception as e:
        logging.error(f"Error verifying description embeddings table: {e}")

async def insert_inventory(conn):
    """Insert inventory data distributed across stores based on customer distribution weights and seasonal trends"""
    try:
        logging.info("Generating inventory with seasonal considerations...")
        
        # Get all stores and products with category and SKU information
        stores_data = await conn.fetch(f"SELECT store_id, store_name, is_online FROM {SCHEMA_NAME}.stores")
        products_data = await conn.fetch(f"""
            SELECT p.product_id, p.sku, c.category_name 
            FROM {SCHEMA_NAME}.products p
            JOIN {SCHEMA_NAME}.categories c ON p.category_id = c.category_id
        """)
        
        # Build SKU to product mapping for quick lookup
        sku_to_product = {row['sku']: row for row in products_data}
        
        # Build category to seasonal multiplier mapping (using average across year for base inventory)
        # This now varies by store based on their climate zone
        def get_category_seasonal_avg(store_name, category_name):
            seasonal_multipliers = get_seasonal_multipliers_for_store_and_category(store_name, category_name)
            return sum(seasonal_multipliers) / len(seasonal_multipliers)
        
        inventory_data = []
        
        # Check if we have consolidated store configuration with product assignments
        has_consolidated_config = True  # stores_reference.json includes product assignments
        logging.info("📦 Using consolidated stores_reference.json for reproducible inventory assignments")
        
        for store in stores_data:
            store_id = store['store_id']
            store_name = store['store_name']
            is_online = store['is_online']
            
            # Get store configuration for inventory distribution
            if is_using_store_ids():
                store_id_key = get_store_id_from_name(store_name)
                store_config = stores.get(store_id_key, {})
            else:
                store_config = stores.get(store_name, {})
            base_stock_multiplier = store_config.get('customer_distribution_weight', 1.0)
            
            # Determine which products this store carries
            if has_consolidated_config and 'product_skus' in store_config:
                # Use configured SKU list from consolidated store data
                assigned_skus = store_config['product_skus']
                selected_products = [sku_to_product[sku] for sku in assigned_skus if sku in sku_to_product]
                logging.info(f"  {store_name}: carrying {len(selected_products)} products (from consolidated config)")
            elif not is_online:
                # Fallback: Randomly select 45-55 products for popup stores
                num_products = random.randint(45, 55)
                selected_products = random.sample(products_data, num_products)
                logging.info(f"  {store_name}: carrying {num_products} of {len(products_data)} total products (random)")
            else:
                # Online store carries all products
                selected_products = products_data
                logging.info(f"  {store_name}: carrying all {len(products_data)} products")
            
            for product in selected_products:
                product_id = product['product_id']
                category_name = product['category_name']
                
                # Get seasonal multiplier for this category based on store's climate zone
                seasonal_multiplier = get_category_seasonal_avg(store_name, category_name)
                
                # Popup stores have limited inventory - much lower stock levels
                # Online stores can have more inventory
                if 'Online' in store_name:
                    # Online store: 30-120 units base stock
                    base_stock = random.randint(30, 120)
                else:
                    # Popup stores: 5-40 units base stock (limited retail space)
                    base_stock = random.randint(5, 40)
                
                # Apply store weight (smaller popup stores have even less)
                # Scale down the multiplier effect for popup stores
                adjusted_multiplier = 0.3 + (base_stock_multiplier / 100.0)  # Much smaller impact
                
                stock_level = int(base_stock * adjusted_multiplier * seasonal_multiplier * random.uniform(0.8, 1.2))
                stock_level = max(2, stock_level)  # Ensure at least 2 items in stock
                
                inventory_data.append((store_id, product_id, stock_level))
        
        await batch_insert(conn, f"INSERT INTO {SCHEMA_NAME}.inventory (store_id, product_id, stock_level) VALUES ($1, $2, $3)", inventory_data)
        
        logging.info(f"Successfully inserted {len(inventory_data):,} inventory records with seasonal adjustments!")
        
    except Exception as e:
        logging.error(f"Error inserting inventory: {e}")
        raise

async def build_product_lookup(conn):
    """Build a lookup table mapping (main_category, product_type, product_name) to product_id"""
    product_lookup = {}
    
    # Get all products with their category and type information
    rows = await conn.fetch(f"""
        SELECT p.product_id, p.product_name, c.category_name, pt.type_name
        FROM {SCHEMA_NAME}.products p
        JOIN {SCHEMA_NAME}.categories c ON p.category_id = c.category_id
        JOIN {SCHEMA_NAME}.product_types pt ON p.type_id = pt.type_id
    """)
    
    for row in rows:
        key = (row['category_name'], row['type_name'], row['product_name'])
        product_lookup[key] = row['product_id']
    
    logging.info(f"Built product lookup with {len(product_lookup)} products")
    return product_lookup

async def insert_orders(conn, num_customers: int = 100000, product_lookup: Optional[Dict] = None):
    """Insert order data into the database with separate orders and order_items tables"""
    
    # Build product lookup if not provided
    if product_lookup is None:
        product_lookup = await build_product_lookup(conn)
    
    logging.info(f"Generating orders for {num_customers:,} customers...")
    
    # Get available product IDs for faster random selection and build category mapping
    product_rows = await conn.fetch(f"""
        SELECT p.product_id, p.cost, p.base_price, c.category_name 
        FROM {SCHEMA_NAME}.products p
        JOIN {SCHEMA_NAME}.categories c ON p.category_id = c.category_id
    """)
    
    product_prices = {row['product_id']: float(row['base_price']) for row in product_rows}
    available_product_ids = list(product_prices.keys())
    
    # Build category to product ID mapping for seasonal selection
    category_products = {}
    for row in product_rows:
        category_name = row['category_name']
        if category_name not in category_products:
            category_products[category_name] = []
        category_products[category_name].append(row['product_id'])
    
    logging.info(f"Built category mapping with {len(category_products)} categories")
    
    total_orders = 0
    orders_data = []
    order_items_data = []
    
    for customer_id in range(1, num_customers + 1):
        # Determine store preference for this customer
        preferred_store = weighted_store_choice()
        store_id = await get_store_id_by_name(conn, preferred_store)
        
        # Get store multipliers
        store_multipliers = get_store_multipliers(preferred_store)
        order_frequency = store_multipliers['orders']
        
        # Determine number of orders for this customer (weighted by store)
        base_orders = random.choices([0, 1, 2, 3, 4, 5], weights=[20, 40, 20, 10, 7, 3], k=1)[0]
        num_orders = max(1, int(base_orders * order_frequency))
        
        for _ in range(num_orders):
            total_orders += 1
            order_id = total_orders
            
            # Generate order date with yearly growth pattern
            year = weighted_year_choice()
            month = random.randint(1, 12)
            
            # Use seasonal category selection for realistic patterns
            selected_category = None
            if seasonal_categories:
                # Choose category based on seasonal multipliers for this month
                # Increase seasonal bias by selecting seasonal category with higher probability
                if random.random() < 0.85:  # 85% seasonal selection
                    selected_category = choose_seasonal_product_category(month, preferred_store)
                else:
                    selected_category = random.choice(list(main_categories.keys()))
            else:
                # No seasonal trends available, use random category selection
                selected_category = random.choice(list(main_categories.keys()))
            
            # Generate random day within the month
            if month == 2:  # February
                max_day = 28 if year % 4 != 0 else 29
            elif month in [4, 6, 9, 11]:  # April, June, September, November
                max_day = 30
            else:
                max_day = 31
            
            day = random.randint(1, max_day)
            order_date = date(year, month, day)
            
            orders_data.append((customer_id, store_id, order_date))
            
            # Generate order items for this order
            num_items = random.choices([1, 2, 3, 4, 5], weights=[40, 30, 15, 10, 5], k=1)[0]
            
            for _ in range(num_items):
                # Select product based on seasonal category preferences
                if seasonal_categories and selected_category in category_products:
                    # Use seasonally-appropriate products with 90% probability (increased from 70%)
                    if random.random() < 0.9:
                        product_id = random.choice(category_products[selected_category])
                    else:
                        # 10% chance to select from any category (for variety)
                        product_id = random.choice(available_product_ids)
                else:
                    # No seasonal data available or category not found, use random selection
                    product_id = random.choice(available_product_ids)
                    
                base_price = product_prices[product_id]
                
                # Generate quantity and pricing
                quantity = random.choices([1, 2, 3, 4, 5], weights=[60, 25, 10, 3, 2], k=1)[0]
                unit_price = base_price * random.uniform(0.8, 1.2)  # Price variation
                
                # Apply discounts occasionally
                discount_percent = 0
                discount_amount = 0
                if random.random() < 0.15:  # 15% chance of discount
                    discount_percent = random.choice([5, 10, 15, 20, 25])
                    discount_amount = (unit_price * quantity * discount_percent) / 100
                
                total_amount = (unit_price * quantity) - discount_amount
                
                order_items_data.append((
                    order_id, store_id, product_id, quantity, unit_price, 
                    discount_percent, discount_amount, total_amount
                ))
        
        # Batch insert every 1000 customers to manage memory
        if customer_id % 1000 == 0:
            if orders_data:
                await batch_insert(conn, f"""
                    INSERT INTO {SCHEMA_NAME}.orders (customer_id, store_id, order_date) 
                    VALUES ($1, $2, $3)
                """, orders_data)
                orders_data = []
            
            if order_items_data:
                await batch_insert(conn, f"""
                    INSERT INTO {SCHEMA_NAME}.order_items 
                    (order_id, store_id, product_id, quantity, unit_price, discount_percent, discount_amount, total_amount) 
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, order_items_data)
                order_items_data = []
            
            if customer_id % 5000 == 0:
                logging.info(f"Processed {customer_id:,} customers, generated {total_orders:,} orders")
    
    # Insert remaining data
    if orders_data:
        await batch_insert(conn, f"""
            INSERT INTO {SCHEMA_NAME}.orders (customer_id, store_id, order_date) 
            VALUES ($1, $2, $3)
        """, orders_data)
    
    if order_items_data:
        await batch_insert(conn, f"""
            INSERT INTO {SCHEMA_NAME}.order_items 
            (order_id, store_id, product_id, quantity, unit_price, discount_percent, discount_amount, total_amount) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """, order_items_data)
    
    logging.info(f"Successfully inserted {total_orders:,} orders!")
    
    # Get order items count
    order_items_count = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.order_items")
    logging.info(f"Successfully inserted {order_items_count:,} order items!")

async def verify_database_contents(conn):
    """Verify database contents and show key statistics"""
    
    logging.info("\n" + "=" * 60)
    logging.info("DATABASE VERIFICATION & STATISTICS")
    logging.info("=" * 60)
    
    # Store distribution verification
    logging.info("\n🏪 STORE SALES DISTRIBUTION:")
    rows = await conn.fetch(f"""
        SELECT s.store_name, 
               COUNT(o.order_id) as orders,
               ROUND(SUM(oi.total_amount)/1000.0, 1) || 'K' as revenue,
               ROUND(100.0 * COUNT(o.order_id) / (SELECT COUNT(*) FROM {SCHEMA_NAME}.orders), 1) || '%' as order_pct
        FROM {SCHEMA_NAME}.orders o 
        JOIN {SCHEMA_NAME}.stores s ON o.store_id = s.store_id
        JOIN {SCHEMA_NAME}.order_items oi ON o.order_id = oi.order_id
        GROUP BY s.store_id, s.store_name
        ORDER BY SUM(oi.total_amount) DESC
    """)
    
    logging.info("   Store               Orders     Revenue    % of Orders")
    logging.info("   " + "-" * 50)
    for row in rows:
        logging.info(f"   {row['store_name']:<18} {row['orders']:>6}     ${row['revenue']:>6}    {row['order_pct']:>6}")
    
    # Year-over-year growth verification
    logging.info("\n📈 YEAR-OVER-YEAR GROWTH PATTERN:")
    rows = await conn.fetch(f"""
        SELECT EXTRACT(YEAR FROM o.order_date) as year,
               COUNT(DISTINCT o.order_id) as orders,
               ROUND(SUM(oi.total_amount)/1000.0, 1) || 'K' as revenue
        FROM {SCHEMA_NAME}.orders o
        JOIN {SCHEMA_NAME}.order_items oi ON o.order_id = oi.order_id
        GROUP BY EXTRACT(YEAR FROM o.order_date)
        ORDER BY year
    """)
    
    logging.info("   Year    Orders     Revenue    Growth")
    logging.info("   " + "-" * 35)
    prev_revenue = None
    for row in rows:
        revenue_num = float(row['revenue'].replace('K', ''))
        growth = ""
        if prev_revenue is not None:
            growth_pct = ((revenue_num - prev_revenue) / prev_revenue) * 100
            growth = f"{growth_pct:+.1f}%"
        logging.info(f"   {int(row['year'])}    {row['orders']:>6}     ${row['revenue']:>6}    {growth:>6}")
        prev_revenue = revenue_num
    
    # Product category distribution
    logging.info("\n🛍️  TOP PRODUCT CATEGORIES:")
    rows = await conn.fetch(f"""
        SELECT c.category_name,
               COUNT(DISTINCT o.order_id) as orders,
               ROUND(SUM(oi.total_amount)/1000.0, 1) || 'K' as revenue
        FROM {SCHEMA_NAME}.categories c
        JOIN {SCHEMA_NAME}.products p ON c.category_id = p.category_id
        JOIN {SCHEMA_NAME}.order_items oi ON p.product_id = oi.product_id
        JOIN {SCHEMA_NAME}.orders o ON oi.order_id = o.order_id
        GROUP BY c.category_id, c.category_name
        ORDER BY SUM(oi.total_amount) DESC
        LIMIT 5
    """)
    
    logging.info("   Category             Orders     Revenue")
    logging.info("   " + "-" * 40)
    for row in rows:
        logging.info(f"   {row['category_name']:<18} {row['orders']:>6}     ${row['revenue']:>6}")
    
    # Supplier analysis
    logging.info("\n🏭 SUPPLIER ANALYSIS:")
    supplier_stats = await conn.fetch(f"""
        SELECT s.supplier_name, s.preferred_vendor, s.supplier_rating,
               COUNT(p.product_id) as product_count,
               ROUND(AVG(p.cost), 2) as avg_product_cost,
               ROUND(SUM(oi.total_amount)/1000.0, 1) || 'K' as revenue_generated
        FROM {SCHEMA_NAME}.suppliers s
        LEFT JOIN {SCHEMA_NAME}.products p ON s.supplier_id = p.supplier_id
        LEFT JOIN {SCHEMA_NAME}.order_items oi ON p.product_id = oi.product_id
        GROUP BY s.supplier_id, s.supplier_name, s.preferred_vendor, s.supplier_rating
        ORDER BY SUM(oi.total_amount) DESC NULLS LAST
        LIMIT 5
    """)
    
    logging.info("   Top Suppliers by Revenue:")
    logging.info("   Supplier                Products  Avg Cost  Revenue  Preferred  Rating")
    logging.info("   " + "-" * 70)
    for row in supplier_stats:
        preferred = "✓" if row['preferred_vendor'] else " "
        logging.info(f"   {row['supplier_name']:<18} {row['product_count']:>8}  ${row['avg_product_cost']:>6}  ${row['revenue_generated']:>6}      {preferred}       {row['supplier_rating']:.1f}")
    
    # Procurement requests summary
    procurement_summary = await conn.fetchrow(f"""
        SELECT COUNT(*) as total_requests,
               COUNT(CASE WHEN approval_status = 'Approved' THEN 1 END) as approved,
               COUNT(CASE WHEN approval_status = 'Pending' THEN 1 END) as pending,
               ROUND(SUM(total_cost)/1000.0, 1) as total_value_k
        FROM {SCHEMA_NAME}.procurement_requests
    """)
    
    if procurement_summary:
        logging.info("\n📋 PROCUREMENT REQUESTS SUMMARY:")
        logging.info(f"   Total Requests:     {procurement_summary['total_requests']:,}")
        logging.info(f"   Approved:           {procurement_summary['approved']:,}")
        logging.info(f"   Pending:            {procurement_summary['pending']:,}")
        logging.info(f"   Total Value:        ${procurement_summary['total_value_k']}K")

    # Final summary
    customers = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.customers")
    products = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.products")
    suppliers = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.suppliers")
    orders = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.orders")
    order_items = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.order_items")
    embeddings = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.product_image_embeddings")
    procurement_requests = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.procurement_requests")
    total_revenue = await conn.fetchval(f"SELECT SUM(total_amount) FROM {SCHEMA_NAME}.order_items")
    
    # Gross margin analysis
    logging.info("\n💰 GROSS MARGIN ANALYSIS:")
    margin_stats = await conn.fetch(f"""
        SELECT 
            COUNT(*) as product_count,
            AVG(cost) as avg_cost,
            AVG(base_price) as avg_selling_price,
            AVG((base_price - cost) / base_price * 100) as avg_gross_margin_percent,
            MIN((base_price - cost) / base_price * 100) as min_gross_margin_percent,
            MAX((base_price - cost) / base_price * 100) as max_gross_margin_percent
        FROM {SCHEMA_NAME}.products
    """)
    
    if margin_stats:
        stats = margin_stats[0]
        logging.info(f"   Average Cost:           ${stats['avg_cost']:.2f}")
        logging.info(f"   Average Selling Price:  ${stats['avg_selling_price']:.2f}")
        logging.info(f"   Average Gross Margin:   {stats['avg_gross_margin_percent']:.1f}%")
        logging.info(f"   Margin Range:           {stats['min_gross_margin_percent']:.1f}% - {stats['max_gross_margin_percent']:.1f}%")
    
    # Calculate total cost and gross profit from actual sales
    sales_margin = await conn.fetchrow(f"""
        SELECT 
            SUM(oi.total_amount) as total_revenue,
            SUM(p.cost * oi.quantity) as total_cost,
            SUM(oi.total_amount) - SUM(p.cost * oi.quantity) as total_gross_profit
        FROM {SCHEMA_NAME}.order_items oi
        JOIN {SCHEMA_NAME}.products p ON oi.product_id = p.product_id
    """)
    
    if sales_margin and sales_margin['total_revenue']:
        actual_margin_pct = (sales_margin['total_gross_profit'] / sales_margin['total_revenue']) * 100
        logging.info(f"   Actual Sales Margin:    {actual_margin_pct:.1f}%")
        logging.info(f"   Total Cost of Goods:    ${sales_margin['total_cost']:.2f}")
        logging.info(f"   Total Gross Profit:     ${sales_margin['total_gross_profit']:.2f}")

    logging.info("\n✅ DATABASE SUMMARY:")
    logging.info(f"   Customers:          {customers:>8,}")
    logging.info(f"   Suppliers:          {suppliers:>8,}")
    logging.info(f"   Products:           {products:>8,}")
    logging.info(f"   Product Embeddings: {embeddings:>8,}")
    logging.info(f"   Orders:             {orders:>8,}")
    logging.info(f"   Order Items:        {order_items:>8,}")
    logging.info(f"   Procurement Reqs:   {procurement_requests:>8,}")
    if total_revenue and orders:
        logging.info(f"   Total Revenue:      ${total_revenue/1000:.1f}K")
        logging.info(f"   Avg Order:          ${total_revenue/orders:.2f}")
        logging.info(f"   Orders/Customer:    {orders/customers:.1f}")
        logging.info(f"   Items/Order:        {order_items/orders:.1f}")

async def verify_seasonal_patterns(conn):
    """Verify that orders and inventory follow seasonal patterns from product data file"""
    
    logging.info("\n" + "=" * 60)
    logging.info("🌱 SEASONAL PATTERNS VERIFICATION")
    logging.info("=" * 60)
    
    try:
        # Test 1: Order seasonality by category and month
        logging.info("\n📊 ORDER SEASONALITY BY CATEGORY:")
        logging.info("   Testing if orders follow seasonal multipliers from product data file")
        
        # Get actual orders by month and category
        rows = await conn.fetch(f"""
            SELECT c.category_name,
                   EXTRACT(MONTH FROM o.order_date) as month,
                   COUNT(DISTINCT o.order_id) as order_count,
                   ROUND(AVG(oi.total_amount), 2) as avg_order_value
            FROM {SCHEMA_NAME}.orders o
            JOIN {SCHEMA_NAME}.order_items oi ON o.order_id = oi.order_id
            JOIN {SCHEMA_NAME}.products p ON oi.product_id = p.product_id
            JOIN {SCHEMA_NAME}.categories c ON p.category_id = c.category_id
            GROUP BY c.category_name, EXTRACT(MONTH FROM o.order_date)
            HAVING COUNT(DISTINCT o.order_id) > 0
            ORDER BY c.category_name, month
        """)
        
        # Organize data by category
        category_data = {}
        for row in rows:
            category = row['category_name']
            month = int(row['month'])
            if category not in category_data:
                category_data[category] = {}
            category_data[category][month] = {
                'order_count': row['order_count'],
                'avg_order_value': float(row['avg_order_value'])
            }
        
        # Compare with seasonal multipliers
        seasonal_matches = 0
        total_seasonal_categories = 0
        
        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        
        # Get seasonal categories from the new system
        if not seasonal_config or 'climate_zones' not in seasonal_config:
            logging.warning("   ⚠️  No seasonal config available for verification")
            return
            
        # Use pacific_northwest as reference for validation (most stores are there)
        pnw_zone = seasonal_config['climate_zones'].get('pacific_northwest', {})
        pnw_categories = pnw_zone.get('categories', {})
        
        for category_name, seasonal_multipliers in pnw_categories.items():
            total_seasonal_categories += 1
            
            if category_name not in category_data:
                logging.warning(f"   ⚠️  No orders found for seasonal category: {category_name}")
                continue
            
            # Find peak and low months from data
            data_months = category_data[category_name]
            if len(data_months) < 6:  # Need reasonable sample size
                logging.warning(f"   ⚠️  Insufficient data for {category_name} ({len(data_months)} months)")
                continue
            
            # Get peak months from multipliers and data
            multiplier_peak_month = seasonal_multipliers.index(max(seasonal_multipliers)) + 1
            multiplier_low_month = seasonal_multipliers.index(min(seasonal_multipliers)) + 1
            
            data_peak_month = max(data_months.keys(), key=lambda m: data_months[m]['order_count'])
            data_low_month = min(data_months.keys(), key=lambda m: data_months[m]['order_count'])
            
            # Check if peaks align (within 3 months tolerance for seasonality to account for data variation)
            peak_match = abs(multiplier_peak_month - data_peak_month) <= 3 or \
                        abs(multiplier_peak_month - data_peak_month) >= 9  # Account for year wraparound
            
            low_match = abs(multiplier_low_month - data_low_month) <= 3 or \
                       abs(multiplier_low_month - data_low_month) >= 9
            
            # Also check if the actual seasonal trend direction is correct (high vs low months)
            data_peak_count = data_months[data_peak_month]['order_count']
            data_low_count = data_months[data_low_month]['order_count']
            
            # Verify the trend direction is correct (peak > low by reasonable margin)
            trend_correct = data_peak_count > data_low_count * 1.1  # At least 10% difference
            
            if (peak_match or low_match) and trend_correct:
                seasonal_matches += 1
                status = "✅"
            elif peak_match or low_match or trend_correct:
                seasonal_matches += 0.5  # Partial credit for trend direction
                status = "⚠️ "
            else:
                status = "❌"
            
            logging.info(f"   {status} {category_name}:")
            logging.info(f"      Expected peak: {month_names[multiplier_peak_month-1]} ({max(seasonal_multipliers):.1f})")
            logging.info(f"      Actual peak:   {month_names[data_peak_month-1]} ({data_months[data_peak_month]['order_count']} orders)")
            logging.info(f"      Expected low:  {month_names[multiplier_low_month-1]} ({min(seasonal_multipliers):.1f})")
            logging.info(f"      Actual low:    {month_names[data_low_month-1]} ({data_months[data_low_month]['order_count']} orders)")
        
        # Test 2: Inventory seasonality
        logging.info("\n📦 INVENTORY SEASONALITY:")
        logging.info("   Testing if inventory levels reflect seasonal patterns")
        
        # Initialize inventory tracking variables
        inventory_matches = 0
        total_inventory_categories = 0
        inventory_match_rate = 0
        
        # Get average inventory by category
        inventory_rows = await conn.fetch(f"""
            SELECT c.category_name,
                   AVG(i.stock_level) as avg_stock,
                   COUNT(*) as product_count
            FROM {SCHEMA_NAME}.inventory i
            JOIN {SCHEMA_NAME}.products p ON i.product_id = p.product_id
            JOIN {SCHEMA_NAME}.categories c ON p.category_id = c.category_id
            GROUP BY c.category_name
            ORDER BY avg_stock DESC
        """)
        
        # Calculate expected inventory ratios based on seasonal averages
        expected_inventory = {}
        if seasonal_config and 'climate_zones' in seasonal_config:
            # Use pacific_northwest as reference for validation
            pnw_zone = seasonal_config['climate_zones'].get('pacific_northwest', {})
            pnw_categories = pnw_zone.get('categories', {})
            
            for category_name, seasonal_multipliers in pnw_categories.items():
                avg_multiplier = sum(seasonal_multipliers) / len(seasonal_multipliers)
                expected_inventory[category_name] = avg_multiplier
        
        # Compare actual vs expected inventory ratios
        inventory_data = {row['category_name']: float(row['avg_stock']) for row in inventory_rows}
        
        if expected_inventory and inventory_data:
            # Normalize both to relative ratios
            base_expected = min(expected_inventory.values())
            base_actual = min(inventory_data.values())
            
            for category_name in expected_inventory:
                if category_name not in inventory_data:
                    continue
                    
                total_inventory_categories += 1
                expected_ratio = expected_inventory[category_name] / base_expected
                actual_ratio = inventory_data[category_name] / base_actual
                
                # Allow 30% tolerance for inventory matching
                ratio_diff = abs(expected_ratio - actual_ratio) / expected_ratio
                if ratio_diff <= 0.3:
                    inventory_matches += 1
                    status = "✅"
                else:
                    status = "❌"
                
                logging.info(f"   {status} {category_name}:")
                logging.info(f"      Expected ratio: {expected_ratio:.2f}")
                logging.info(f"      Actual ratio:   {actual_ratio:.2f}")
                logging.info(f"      Avg stock:      {inventory_data[category_name]:.1f}")
        
        # Calculate inventory match rate
        if total_inventory_categories > 0:
            inventory_match_rate = (inventory_matches / total_inventory_categories) * 100
        
        # Test 3: Monthly order distribution
        logging.info("\n📈 MONTHLY ORDER DISTRIBUTION:")
        monthly_totals = await conn.fetch(f"""
            SELECT EXTRACT(MONTH FROM o.order_date) as month,
                   COUNT(DISTINCT o.order_id) as total_orders
            FROM {SCHEMA_NAME}.orders o
            GROUP BY EXTRACT(MONTH FROM o.order_date)
            ORDER BY month
        """)
        
        if monthly_totals:
            total_orders = sum(row['total_orders'] for row in monthly_totals)
            logging.info("   Month    Orders    % of Total")
            logging.info("   " + "-" * 30)
            for row in monthly_totals:
                month_num = int(row['month'])
                pct = (row['total_orders'] / total_orders) * 100
                logging.info(f"   {month_names[month_num-1]:<6} {row['total_orders']:>8}    {pct:>6.1f}%")
        
        # Summary
        logging.info("\n🎯 SEASONAL VERIFICATION SUMMARY:")
        if total_seasonal_categories > 0:
            order_match_rate = (seasonal_matches / total_seasonal_categories) * 100
            logging.info(f"   Order seasonality match rate: {seasonal_matches}/{total_seasonal_categories} ({order_match_rate:.1f}%)")
        
        if total_inventory_categories > 0:
            logging.info(f"   Inventory seasonality match rate: {inventory_matches}/{total_inventory_categories} ({inventory_match_rate:.1f}%)")
        
        # Overall assessment
        if total_seasonal_categories > 0 and seasonal_matches >= total_seasonal_categories * 0.7:
            logging.info("   ✅ SEASONAL PATTERNS VERIFIED: Orders follow expected seasonal trends")
        else:
            logging.info("   ⚠️  SEASONAL PATTERNS PARTIAL: Some discrepancies found in seasonal trends")
        
        if inventory_match_rate >= 70:
            logging.info("   ✅ INVENTORY SEASONALITY VERIFIED: Stock levels reflect seasonal patterns")
        else:
            logging.info("   ⚠️  INVENTORY SEASONALITY PARTIAL: Some discrepancies in seasonal stock levels")
            
    except Exception as e:
        logging.error(f"Error verifying seasonal patterns: {e}")
        raise

async def recreate_database():
    """Drop and recreate the zava database"""
    try:
        # Connect to postgres database to drop/create zava
        logging.info("Connecting to postgres database to recreate zava...")
        conn = await asyncpg.connect(
            host=POSTGRES_CONFIG['host'],
            port=POSTGRES_CONFIG['port'],
            database='postgres',  # Connect to postgres database
            user=POSTGRES_CONFIG['user'],
            password=POSTGRES_CONFIG['password']
        )
        
        try:
            # Terminate existing connections to zava database
            logging.info("Terminating existing connections to zava database...")
            await conn.execute("""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = 'zava'
                  AND pid <> pg_backend_pid()
            """)
            
            # Drop database if it exists
            logging.info("Dropping database 'zava' if it exists...")
            await conn.execute("DROP DATABASE IF EXISTS zava")
            logging.info("✓ Database dropped")
            
            # Create database
            logging.info("Creating database 'zava'...")
            await conn.execute("CREATE DATABASE zava")
            logging.info("✓ Database created")
            
        finally:
            await conn.close()
            
    except Exception as e:
        logging.error(f"Error recreating database: {e}")
        raise

async def generate_postgresql_database(num_customers: int = 50000):
    """Generate complete PostgreSQL database"""
    try:
        # Drop and recreate the database first
        await recreate_database()
        
        # Create connection to the new database
        conn = await create_connection()
        
        try:
            # Drop existing tables to start fresh (optional)
            logging.info("Dropping existing tables if they exist...")
            await conn.execute(f"DROP SCHEMA IF EXISTS {SCHEMA_NAME} CASCADE")
            
            await create_database_schema(conn)
            await insert_stores(conn)
            await insert_categories(conn)
            await insert_product_types(conn)
            await insert_suppliers(conn)
            await insert_customers(conn, num_customers)
            await insert_products(conn)
            
            # Insert agent support data (now that products table exists)
            logging.info("\n" + "=" * 50)
            logging.info("INSERTING AGENT SUPPORT DATA")
            logging.info("=" * 50)
            await insert_agent_support_data(conn)
            
            # Populate product embeddings from product data file
            logging.info("\n" + "=" * 50)
            logging.info("POPULATING PRODUCT EMBEDDINGS")
            logging.info("=" * 50)
            await populate_product_image_embeddings(conn, clear_existing=True)
            await populate_product_description_embeddings(conn, clear_existing=True)
            
            # Verify embeddings were populated
            logging.info("\n" + "=" * 50)
            logging.info("VERIFYING PRODUCT EMBEDDINGS")
            logging.info("=" * 50)
            await verify_embeddings_table(conn)
            await verify_description_embeddings_table(conn)
            
            # Insert inventory data
            logging.info("\n" + "=" * 50)
            logging.info("INSERTING INVENTORY DATA")
            logging.info("=" * 50)
            await insert_inventory(conn)
            
            # Insert order data
            logging.info("\n" + "=" * 50)
            logging.info("INSERTING ORDER DATA")
            logging.info("=" * 50)
            await insert_orders(conn, num_customers)
            
            # Create supplier views for optimized queries
            logging.info("\n" + "=" * 50)
            logging.info("CREATING SUPPLIER VIEWS")
            logging.info("=" * 50)
            await create_supplier_views(conn)
            
            # Verify the database was created and has data
            logging.info("\n" + "=" * 50)
            logging.info("FINAL DATABASE VERIFICATION")
            logging.info("=" * 50)
            await verify_database_contents(conn)
            
            # Verify seasonal patterns are working
            await verify_seasonal_patterns(conn)
            
            logging.info("\n" + "=" * 50)
            logging.info("DATABASE GENERATION COMPLETE")
            logging.info("=" * 50)
            
            logging.info("Database generation completed successfully.")
        except Exception as e:
            logging.error(f"Error during database generation: {e}")
            raise
        finally:
            await conn.close()
            logging.info("Database connection closed.")

    except Exception as e:
        logging.error(f"Failed to generate database: {e}")
        raise

async def show_database_stats():
    """Show database statistics"""
    
    logging.info("\n" + "=" * 40)
    logging.info("DATABASE STATISTICS")
    logging.info("=" * 40)
    
    conn = await create_connection()
    
    try:
        # Get table row counts
        customers_count = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.customers")
        suppliers_count = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.suppliers")
        products_count = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.products")
        orders_count = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.orders")
        order_items_count = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.order_items")
        embeddings_count = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.product_image_embeddings")
        procurement_count = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.procurement_requests")
        
        # Get revenue information
        total_revenue = await conn.fetchval(f"SELECT SUM(total_amount) FROM {SCHEMA_NAME}.order_items")
        if total_revenue is None:
            total_revenue = 0
            
        # Count indexes
        index_count = await conn.fetchval(f"""
            SELECT COUNT(*) FROM pg_indexes 
            WHERE schemaname = '{SCHEMA_NAME}' AND indexname LIKE 'idx_%'
        """)
        
        # Get database size
        db_size = await conn.fetchval(f"""
            SELECT pg_size_pretty(pg_database_size('{POSTGRES_CONFIG['database']}'))
        """)
        
        logging.info(f"Database Size: {db_size}")
        logging.info(f"Customers: {customers_count:,}")
        logging.info(f"Suppliers: {suppliers_count:,}")
        logging.info(f"Products: {products_count:,}")
        logging.info(f"Product Embeddings: {embeddings_count:,}")
        logging.info(f"Orders: {orders_count:,}")
        logging.info(f"Order Items: {order_items_count:,}")
        logging.info(f"Procurement Requests: {procurement_count:,}")
        logging.info(f"Total Revenue: ${total_revenue:,.2f}")
        if orders_count > 0:
            logging.info(f"Average Order Value: ${total_revenue/orders_count:.2f}")
            logging.info(f"Orders per Customer: {orders_count/customers_count:.1f}")
            logging.info(f"Items per Order: {order_items_count/orders_count:.1f}")
        logging.info(f"Performance Indexes: {index_count}")
        
        # Show sample embeddings if they exist
        if embeddings_count > 0:
            await verify_embeddings_table(conn)
        
    finally:
        await conn.close()

async def demo_supplier_procurement_queries():
    """
    Demonstration function showing supplier and procurement queries for enterprise use cases.
    
    This function demonstrates:
    1. Supplier evaluation and selection
    2. Procurement request analysis
    3. Bulk discount opportunities
    4. ESG compliance reporting
    5. Lead time analysis
    """
    conn = await create_connection()
    
    try:
        logging.info("\n" + "=" * 70)
        logging.info("ENTERPRISE PROCUREMENT & SUPPLIER ANALYSIS DEMONSTRATION")
        logging.info("=" * 70)
        
        # 1. Top Suppliers by Performance Score
        logging.info("\n🏆 TOP SUPPLIERS BY PERFORMANCE SCORE:")
        top_suppliers = await conn.fetch(f"""
            SELECT s.supplier_name, s.supplier_code, s.preferred_vendor, s.esg_compliant,
                   ROUND(AVG(sp.overall_score), 2) as avg_performance,
                   COUNT(p.product_id) as product_count,
                   s.bulk_discount_threshold, s.bulk_discount_percent
            FROM {SCHEMA_NAME}.suppliers s
            LEFT JOIN {SCHEMA_NAME}.supplier_performance sp ON s.supplier_id = sp.supplier_id
            LEFT JOIN {SCHEMA_NAME}.products p ON s.supplier_id = p.supplier_id
            WHERE s.active_status = true AND s.approved_vendor = true
            GROUP BY s.supplier_id, s.supplier_name, s.supplier_code, s.preferred_vendor, 
                     s.esg_compliant, s.bulk_discount_threshold, s.bulk_discount_percent
            ORDER BY avg_performance DESC NULLS LAST, s.preferred_vendor DESC
            LIMIT 5
        """)
        
        logging.info("   Supplier              Code    Preferred  ESG   Performance  Products  Bulk Discount")
        logging.info("   " + "-" * 80)
        for supplier in top_suppliers:
            preferred = "✓" if supplier['preferred_vendor'] else " "
            esg = "✓" if supplier['esg_compliant'] else " "
            performance = supplier['avg_performance'] if supplier['avg_performance'] else "N/A"
            logging.info(f"   {supplier['supplier_name']:<18} {supplier['supplier_code']:<8} {preferred:>3}       {esg:>3}      {performance:>6}     {supplier['product_count']:>5}      {supplier['bulk_discount_percent']}%@${supplier['bulk_discount_threshold']:.0f}")
        
        # 2. Procurement Requests Analysis
        logging.info("\n📋 PROCUREMENT REQUESTS BY STATUS & URGENCY:")
        procurement_analysis = await conn.fetch(f"""
            SELECT approval_status, urgency_level, 
                   COUNT(*) as request_count,
                   ROUND(SUM(total_cost), 2) as total_value,
                   ROUND(AVG(total_cost), 2) as avg_request_value
            FROM {SCHEMA_NAME}.procurement_requests
            GROUP BY approval_status, urgency_level
            ORDER BY approval_status, urgency_level DESC
        """)
        
        current_status = None
        for req in procurement_analysis:
            if req['approval_status'] != current_status:
                current_status = req['approval_status']
                logging.info(f"\n   {current_status.upper()}:")
                logging.info("     Priority   Count     Total Value    Avg Value")
                logging.info("     " + "-" * 45)
            
            logging.info(f"     {req['urgency_level']:<8} {req['request_count']:>5}     ${req['total_value']:>10,.2f}    ${req['avg_request_value']:>8,.2f}")
        
        # 3. Bulk Discount Opportunities
        logging.info("\n💰 BULK DISCOUNT OPPORTUNITIES:")
        bulk_opportunities = await conn.fetch(f"""
            SELECT s.supplier_name, s.bulk_discount_threshold, s.bulk_discount_percent,
                   SUM(pr.total_cost) as pending_value,
                   COUNT(pr.request_id) as pending_requests,
                   CASE 
                     WHEN SUM(pr.total_cost) >= s.bulk_discount_threshold 
                     THEN ROUND(SUM(pr.total_cost) * s.bulk_discount_percent / 100, 2)
                     ELSE 0 
                   END as potential_savings
            FROM {SCHEMA_NAME}.suppliers s
            JOIN {SCHEMA_NAME}.procurement_requests pr ON s.supplier_id = pr.supplier_id
            WHERE pr.approval_status = 'Approved' AND pr.bulk_discount_eligible = true
            GROUP BY s.supplier_id, s.supplier_name, s.bulk_discount_threshold, s.bulk_discount_percent
            HAVING SUM(pr.total_cost) >= s.bulk_discount_threshold * 0.7  -- Within 70% of threshold
            ORDER BY potential_savings DESC
        """)
        
        if bulk_opportunities:
            logging.info("   Supplier              Threshold    Pending Value    Potential Savings")
            logging.info("   " + "-" * 65)
            total_savings = 0
            for opp in bulk_opportunities:
                total_savings += float(opp['potential_savings'])
                logging.info(f"   {opp['supplier_name']:<18}   ${opp['bulk_discount_threshold']:>8,.0f}    ${opp['pending_value']:>11,.2f}      ${opp['potential_savings']:>9,.2f}")
            logging.info("   " + "-" * 65)
            logging.info(f"   TOTAL POTENTIAL SAVINGS:                                ${total_savings:>9,.2f}")
        else:
            logging.info("   No current bulk discount opportunities found")
        
        # 4. ESG Compliance Report
        logging.info("\n🌱 ESG COMPLIANCE ANALYSIS:")
        esg_analysis = await conn.fetch(f"""
            SELECT 
                COUNT(CASE WHEN s.esg_compliant = true THEN 1 END) as esg_compliant_suppliers,
                COUNT(CASE WHEN s.esg_compliant = false THEN 1 END) as non_esg_suppliers,
                COUNT(pr.request_id) as total_requests,
                COUNT(CASE WHEN pr.esg_requirements = true THEN 1 END) as esg_required_requests,
                COUNT(CASE WHEN pr.esg_requirements = true AND s.esg_compliant = true THEN 1 END) as esg_compliant_requests
            FROM {SCHEMA_NAME}.suppliers s
            LEFT JOIN {SCHEMA_NAME}.procurement_requests pr ON s.supplier_id = pr.supplier_id
        """)
        
        esg_data = esg_analysis[0] if esg_analysis else {}
        if esg_data:
            esg_compliance_rate = (esg_data['esg_compliant_requests'] / max(esg_data['esg_required_requests'], 1)) * 100
            logging.info(f"   ESG Compliant Suppliers:    {esg_data['esg_compliant_suppliers']}")
            logging.info(f"   Non-ESG Suppliers:          {esg_data['non_esg_suppliers']}")
            logging.info(f"   ESG Required Requests:      {esg_data['esg_required_requests']}")
            logging.info(f"   ESG Compliance Rate:        {esg_compliance_rate:.1f}%")
        
        # 5. Lead Time Analysis
        logging.info("\n⏱️  SUPPLIER LEAD TIME ANALYSIS:")
        lead_time_analysis = await conn.fetch(f"""
            SELECT s.supplier_name, s.lead_time_days,
                   COUNT(p.product_id) as product_count,
                   ROUND(AVG(p.procurement_lead_time_days), 1) as avg_product_lead_time,
                   COUNT(pr.request_id) as active_requests
            FROM {SCHEMA_NAME}.suppliers s
            LEFT JOIN {SCHEMA_NAME}.products p ON s.supplier_id = p.supplier_id
            LEFT JOIN {SCHEMA_NAME}.procurement_requests pr ON s.supplier_id = pr.supplier_id 
                AND pr.approval_status IN ('Approved', 'Pending')
            WHERE s.active_status = true
            GROUP BY s.supplier_id, s.supplier_name, s.lead_time_days
            ORDER BY s.lead_time_days, s.supplier_name
            LIMIT 8
        """)
        
        logging.info("   Supplier              Lead Time    Products    Avg Product Lead    Active Reqs")
        logging.info("   " + "-" * 75)
        for lt in lead_time_analysis:
            logging.info(f"   {lt['supplier_name']:<18}   {lt['lead_time_days']:>7} days    {lt['product_count']:>7}         {lt['avg_product_lead_time']:>8} days      {lt['active_requests']:>6}")
        
        # 6. Procurement Workflow Efficiency
        logging.info("\n⚡ PROCUREMENT WORKFLOW EFFICIENCY:")
        workflow_stats = await conn.fetchrow(f"""
            SELECT 
                ROUND(AVG(CASE WHEN approval_status = 'Approved' AND approved_at IS NOT NULL 
                              THEN EXTRACT(DAYS FROM (approved_at - request_date)) 
                              ELSE NULL END), 1) as avg_approval_days,
                COUNT(CASE WHEN approval_status = 'Approved' THEN 1 END) as approved_count,
                COUNT(CASE WHEN approval_status = 'Pending' AND request_date < CURRENT_DATE - INTERVAL '7 days' THEN 1 END) as overdue_pending,
                COUNT(CASE WHEN urgency_level = 'Critical' AND approval_status = 'Pending' THEN 1 END) as critical_pending
            FROM {SCHEMA_NAME}.procurement_requests
        """)
        
        if workflow_stats:
            logging.info(f"   Average Approval Time:      {workflow_stats['avg_approval_days']} days")
            logging.info(f"   Total Approved Requests:    {workflow_stats['approved_count']}")
            logging.info(f"   Overdue Pending Requests:   {workflow_stats['overdue_pending']}")
            logging.info(f"   Critical Pending Requests:  {workflow_stats['critical_pending']}")
        
        logging.info("\n" + "=" * 70)
        logging.info("PROCUREMENT ANALYSIS COMPLETE")
        logging.info("=" * 70)
        
    finally:
        await conn.close()

async def main():
    """Main function to handle command line arguments"""
    
    parser = argparse.ArgumentParser(description='Generate PostgreSQL database with product embeddings')
    parser.add_argument('--show-stats', action='store_true', 
                       help='Show database statistics instead of generating')
    parser.add_argument('--embeddings-only', action='store_true',
                       help='Only populate product embeddings (database must already exist)')
    parser.add_argument('--verify-embeddings', action='store_true',
                       help='Only verify embeddings table and show sample data')
    parser.add_argument('--verify-seasonal', action='store_true',
                       help='Only verify seasonal patterns in existing database')
    parser.add_argument('--demo-procurement', action='store_true',
                       help='Demonstrate procurement and supplier analysis queries')
    parser.add_argument('--clear-embeddings', action='store_true',
                       help='Clear existing embeddings before populating (used with --embeddings-only)')
    parser.add_argument('--batch-size', type=int, default=100,
                       help='Batch size for processing embeddings (default: 100)')
    parser.add_argument('--num-customers', type=int, default=50000,
                       help='Number of customers to generate (default: 50000)')
    
    args = parser.parse_args()
    
    try:
        if args.show_stats:
            # Show database statistics
            await show_database_stats()
        elif args.verify_embeddings:
            # Verify embeddings only
            conn = await create_connection()
            try:
                await verify_embeddings_table(conn)
                await verify_description_embeddings_table(conn)
            finally:
                await conn.close()
        elif args.verify_seasonal:
            # Verify seasonal patterns only
            conn = await create_connection()
            try:
                await verify_seasonal_patterns(conn)
            finally:
                await conn.close()
        elif args.demo_procurement:
            # Demo procurement and supplier analysis
            await demo_supplier_procurement_queries()
        elif args.embeddings_only:
            # Populate embeddings only
            conn = await create_connection()
            try:
                await populate_product_image_embeddings(conn, clear_existing=args.clear_embeddings, batch_size=args.batch_size)
                await populate_product_description_embeddings(conn, clear_existing=args.clear_embeddings, batch_size=args.batch_size)
                await verify_embeddings_table(conn)
                await verify_description_embeddings_table(conn)
            finally:
                await conn.close()
        else:
            # Generate the complete database
            logging.info(f"Database will be created at {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}")
            logging.info(f"Schema: {SCHEMA_NAME}")
            await generate_postgresql_database(num_customers=args.num_customers)
            
            logging.info("\nDatabase generated successfully!")
            logging.info(f"Host: {POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}")
            logging.info(f"Database: {POSTGRES_CONFIG['database']}")
            logging.info(f"Schema: {SCHEMA_NAME}")
            logging.info(f"To view statistics: python {sys.argv[0]} --show-stats")
            logging.info(f"To populate embeddings only: python {sys.argv[0]} --embeddings-only")
            logging.info(f"To verify embeddings: python {sys.argv[0]} --verify-embeddings")
            logging.info(f"To verify seasonal patterns: python {sys.argv[0]} --verify-seasonal")
            logging.info(f"To demo procurement queries: python {sys.argv[0]} --demo-procurement")
            
    except Exception as e:
        logging.error(f"Failed to complete operation: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check if required packages are available
    try:
        # Note: Faker and dotenv are already imported at the top of the file
        pass
    except ImportError as e:
        logging.error(f"Required library not found: {e}")
        logging.error("Please install required packages with: pip install -r requirements_postgres.txt")
        exit(1)
    
    asyncio.run(main())


# =============================================================================
# ROW LEVEL SECURITY HELPER FUNCTIONS FOR WORKSHOP/DEMO
# =============================================================================

async def demo_row_level_security():
    """
    Demonstration function showing how Row Level Security works with store managers.
    
    This function shows how to:
    1. Set a manager context
    2. Query data that will be filtered by RLS policies
    3. Switch to a different manager and see different results
    
    Usage for workshop:
        python -c "import asyncio; from generate_zava_postgres import demo_row_level_security; asyncio.run(demo_row_level_security())"
    """
    conn = await create_connection()
    
    try:
        # Get all stores and their manager IDs
        stores_info = await conn.fetch(f"""
            SELECT store_name, rls_user_id 
            FROM {SCHEMA_NAME}.stores 
            ORDER BY store_name
        """)
        
        print("\n" + "=" * 60)
        print("ROW LEVEL SECURITY DEMONSTRATION")
        print("=" * 60)
        
        print("\nAvailable stores and their manager IDs:")
        for store in stores_info:
            print(f"  {store['store_name']}: {store['rls_user_id']}")
        
        # Demo with first two stores
        if len(stores_info) >= 2:
            store1 = stores_info[0]
            store2 = stores_info[1]
            
            print(f"\n--- Demonstrating RLS for {store1['store_name']} ---")
            await demo_manager_view(conn, store1['rls_user_id'], store1['store_name'])
            
            print(f"\n--- Demonstrating RLS for {store2['store_name']} ---")
            await demo_manager_view(conn, store2['rls_user_id'], store2['store_name'])
            
        print("\n" + "=" * 60)
        print("RLS DEMONSTRATION COMPLETE")
        print("=" * 60)
        
    finally:
        await conn.close()

async def demo_manager_view(conn, rls_user_id: str, store_name: str):
    """
    Demonstrate what a specific store manager can see with RLS enabled.
    """
    # Set the manager context
    await conn.execute("SELECT set_config('app.current_rls_user_id', $1, false)", rls_user_id)
    
    # Query orders (should only see orders from their store)
    orders = await conn.fetchval(f"""
        SELECT COUNT(*) FROM {SCHEMA_NAME}.orders
    """)
    
    # Query customers with breakdown
    direct_customers = await conn.fetchval(f"""
        SELECT COUNT(*) FROM {SCHEMA_NAME}.customers 
        WHERE primary_store_id IS NOT NULL
    """)
    
    indirect_customers = await conn.fetchval(f"""
        SELECT COUNT(*) FROM {SCHEMA_NAME}.customers 
        WHERE primary_store_id IS NULL
    """)
    
    total_customers = await conn.fetchval(f"""
        SELECT COUNT(*) FROM {SCHEMA_NAME}.customers
    """)
    
    # Query inventory (should only see their store's inventory)
    inventory_items = await conn.fetchval(f"""
        SELECT COUNT(*) FROM {SCHEMA_NAME}.inventory
    """)
    
    # Get total revenue
    total_revenue = await conn.fetchval(f"""
        SELECT COALESCE(SUM(oi.total_amount), 0)
        FROM {SCHEMA_NAME}.order_items oi
        JOIN {SCHEMA_NAME}.orders o ON oi.order_id = o.order_id
    """)
    
    print(f"  Manager ID: {rls_user_id}")
    print(f"  Store: {store_name}")
    print(f"  Visible Orders: {orders:,}")
    print(f"  Visible Customers: {total_customers:,}")
    print(f"    - Directly assigned: {direct_customers:,}")
    print(f"    - Discovered via orders: {indirect_customers:,}")
    print(f"  Visible Inventory Items: {inventory_items:,}")
    print(f"  Total Revenue: ${total_revenue:,.2f}")

async def test_customer_security():
    """
    Test the customer security model by demonstrating different access patterns.
    """
    conn = await create_connection()
    
    try:
        print("\n" + "=" * 60)
        print("CUSTOMER SECURITY MODEL TEST")
        print("=" * 60)
        
        # Get store information
        stores_info = await conn.fetch(f"""
            SELECT s.store_name, s.rls_user_id,
                   COUNT(c.customer_id) as assigned_customers
            FROM {SCHEMA_NAME}.stores s
            LEFT JOIN {SCHEMA_NAME}.customers c ON s.store_id = c.primary_store_id
            GROUP BY s.store_id, s.store_name, s.rls_user_id
            ORDER BY assigned_customers DESC
        """)
        
        print("\nCustomer assignment summary:")
        for store in stores_info:
            print(f"  {store['store_name']}: {store['assigned_customers']:,} directly assigned customers")
        
        # Test with the first store
        if stores_info:
            test_store = stores_info[0]
            print(f"\n--- Testing access for {test_store['store_name']} ---")
            
            # Set manager context
            await conn.execute("SELECT set_config('app.current_rls_user_id', $1, false)", test_store['rls_user_id'])
            
            # Test direct customer access
            direct_access = await conn.fetch(f"""
                SELECT customer_id, first_name, last_name, email, primary_store_id
                FROM {SCHEMA_NAME}.customers 
                WHERE primary_store_id IS NOT NULL
                LIMIT 3
            """)
            
            print("  Direct customer access (assigned to store):")
            for customer in direct_access:
                print(f"    - {customer['first_name']} {customer['last_name']} ({customer['email']}) - Store ID: {customer['primary_store_id']}")
            
            # Test indirect customer access (through orders)
            indirect_access = await conn.fetch(f"""
                SELECT DISTINCT c.customer_id, c.first_name, c.last_name, c.email, c.primary_store_id
                FROM {SCHEMA_NAME}.customers c
                WHERE c.primary_store_id IS NULL
                LIMIT 3
            """)
            
            if indirect_access:
                print("  Indirect customer access (discovered via orders):")
                for customer in indirect_access:
                    store_ref = customer['primary_store_id'] if customer['primary_store_id'] else "No primary store"
                    print(f"    - {customer['first_name']} {customer['last_name']} ({customer['email']}) - {store_ref}")
            else:
                print("  No indirect customers visible (haven't ordered from this store)")
            
            # Test with a different manager
            if len(stores_info) > 1:
                other_store = stores_info[1]
                print(f"\n--- Switching to {other_store['store_name']} ---")
                await conn.execute("SELECT set_config('app.current_rls_user_id', $1, false)", other_store['rls_user_id'])
                
                visible_customers = await conn.fetchval(f"SELECT COUNT(*) FROM {SCHEMA_NAME}.customers")
                print(f"  Customers visible to {other_store['store_name']} manager: {visible_customers:,}")
        
        print("\n" + "=" * 60)
        print("CUSTOMER SECURITY TEST COMPLETE")
        print("=" * 60)
        
    finally:
        await conn.close()

async def set_manager_context(rls_user_id: str):
    """
    Helper function to set the manager context for RLS.
    
    Usage in your application:
        await set_manager_context("12345678-1234-1234-1234-123456789012")
    """
    conn = await create_connection()
    try:
        await conn.execute("SELECT set_config('app.current_rls_user_id', $1, false)", rls_user_id)
        print(f"Manager context set to: {rls_user_id}")
    finally:
        await conn.close()

async def get_manager_ids():
    """
    Helper function to get all manager IDs for workshop use.
    
    Returns a dictionary mapping store names to manager IDs.
    """
    conn = await create_connection()
    try:
        stores = await conn.fetch(f"""
            SELECT store_name, rls_user_id::text as rls_user_id
            FROM {SCHEMA_NAME}.stores 
            ORDER BY store_name
        """)
        return {store['store_name']: store['rls_user_id'] for store in stores}
    finally:
        await conn.close()


# Workshop example usage:
#
# 1. Get manager IDs:
#    manager_ids = asyncio.run(get_manager_ids())
#    print(manager_ids)
#
# 2. Demo RLS:
#    asyncio.run(demo_row_level_security())
#
# 3. Set context in your app:
#    asyncio.run(set_manager_context("your-manager-id-here"))
#
# 4. Then all subsequent queries will be filtered by RLS policies
