"""
Customer Sales Database Generator for SQLite using SQLAlchemy ORM

This script generates a comprehensive customer sales database with optimized indexing
for SQLite using SQLAlchemy ORM models.

DATA FILE STRUCTURE (all in reference_data/ folder):
- stores_reference.json: Consolidated store configurations, product assignments, and seasonal data
- product_data.json: Contains all product information (main_categories with products)
- supplier_data.json: Contains supplier information for clothing/apparel vendors
- seasonal_multipliers.json: Contains seasonal adjustment factors for different climate zones

SQLITE CONNECTION:
- Uses SQLAlchemy ORM (declarative models)
- Creates or connects to retail.db SQLite database file
- Targets all tables in the database (no schema concept in SQLite)

FEATURES:
- Complete database generation with customers, products, stores, orders
- Product image embeddings population from product_data.json
- Product description embeddings population from product_data.json
- Performance-optimized indexes
- Comprehensive statistics and verification
- Reproducible store product assignments (via store_products.json)

USAGE:
    python generate_github_sqlite_sqlalchemy.py                     # Generate complete database
    python generate_github_sqlite_sqlalchemy.py --show-stats        # Show database statistics
"""

import json
import logging
import os
import random
import sys
from datetime import date, timedelta
from typing import List

from dotenv import load_dotenv
from faker import Faker
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session

# Add the workspace root to Python path for importing models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.models.sqlite import (
    Base, Store, Category, ProductType, Product, Supplier, Customer,
    Order, OrderItem, Inventory, Approver, SupplierContract,
    SupplierPerformance, CompanyPolicy, ProcurementRequest, Notification
)

# Load environment variables
script_dir = os.path.dirname(os.path.abspath(__file__))
env_paths = [
    os.path.join(script_dir, '.env'),
    os.path.join(script_dir, '..', '..', '.env'),
]

for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        break
else:
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

# SQLite configuration
SQLITE_DB_FILE = os.getenv('SQLITE_DB_FILE', os.path.join(os.path.dirname(__file__), '..', 'retail.db'))

# Super Manager UUID - has access to all rows
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

def get_store_name_from_id(store_id: str) -> str:
    """Get store name from store ID"""
    if store_id in stores:
        return stores[store_id].get('store_name', store_id)
    return store_id

def get_store_id_from_name(store_name: str) -> str:
    """Get store ID from store name"""
    for store_id, config in stores.items():
        if config.get('store_name') == store_name:
            return store_id
    return store_name

def is_using_store_ids() -> bool:
    """Check if we're using the new ID-based format"""
    first_store_key = next(iter(stores.keys()))
    return 'store_name' in stores[first_store_key]

def weighted_store_choice():
    """Choose a store based on weighted distribution"""
    store_keys = list(stores.keys())
    weights = [stores[store]['customer_distribution_weight'] for store in store_keys]
    selected_key = random.choices(store_keys, weights=weights, k=1)[0]
    
    if is_using_store_ids():
        return get_store_name_from_id(selected_key)
    else:
        return selected_key

def generate_phone_number(region=None):
    """Generate a phone number in North American format (XXX) XXX-XXXX"""
    return f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"

def create_engine_and_session():
    """Create SQLAlchemy engine and session"""
    try:
        # Create SQLite database URL
        db_url = f"sqlite:///{SQLITE_DB_FILE}"
        
        # Create engine
        engine = create_engine(db_url, echo=False)
        
        # Create session factory
        SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        
        logging.info(f"Connected to SQLite database: {SQLITE_DB_FILE}")
        
        return engine, SessionLocal
    except Exception as e:
        logging.error(f"Failed to connect to SQLite: {e}")
        raise

def create_database_schema(engine):
    """Create database schema using SQLAlchemy models"""
    try:
        logging.info("Creating database schema from SQLAlchemy models...")
        
        # Create all tables defined in the models
        Base.metadata.create_all(engine)
        
        logging.info("Database schema created successfully from SQLAlchemy models!")
        
    except Exception as e:
        logging.error(f"Error creating database schema: {e}")
        raise

def bulk_insert_objects(session: Session, objects: List, batch_size: int = 1000):
    """Insert objects in batches using SQLAlchemy bulk operations"""
    try:
        for i in range(0, len(objects), batch_size):
            batch = objects[i:i + batch_size]
            session.bulk_save_objects(batch)
            session.flush()
        session.commit()
    except Exception as e:
        session.rollback()
        raise e

def insert_stores(session: Session):
    """Insert store data into the database"""
    try:
        logging.info("Generating stores...")
        
        store_objects = []
        
        for store_key, store_config in stores.items():
            if is_using_store_ids():
                store_name = store_config.get('store_name', store_key)
            else:
                store_name = store_key
            
            is_online = "online" in store_name.lower()
            rls_user_id = store_config.get('rls_user_id')
            if not rls_user_id:
                raise ValueError(f"No rls_user_id found for store: {store_name}")
            
            store_objects.append(Store(
                store_name=store_name,
                rls_user_id=rls_user_id,
                is_online=is_online
            ))
        
        bulk_insert_objects(session, store_objects)
        
        # Log store manager IDs
        stores_in_db = session.query(Store).order_by(Store.store_name).all()
        logging.info("Store Manager IDs (for workshop use):")
        for store in stores_in_db:
            logging.info(f"  {store.store_name}: {store.rls_user_id}")
        
        logging.info(f"Successfully inserted {len(store_objects):,} stores!")
    except Exception as e:
        logging.error(f"Error inserting stores: {e}")
        raise

def insert_categories(session: Session):
    """Insert category data into the database"""
    try:
        logging.info("Generating categories...")
        
        category_objects = []
        
        for main_category in main_categories.keys():
            category_objects.append(Category(category_name=main_category))
        
        bulk_insert_objects(session, category_objects)
        
        logging.info(f"Successfully inserted {len(category_objects):,} categories!")
    except Exception as e:
        logging.error(f"Error inserting categories: {e}")
        raise

def insert_product_types(session: Session):
    """Insert product type data into the database"""
    try:
        logging.info("Generating product types...")
        
        # Get category mapping
        categories_in_db = session.query(Category).all()
        category_mapping = {cat.category_name: cat.category_id for cat in categories_in_db}
        
        product_type_objects = []
        
        for main_category, subcategories in main_categories.items():
            category_id = category_mapping[main_category]
            for subcategory in subcategories.keys():
                product_type_objects.append(ProductType(
                    category_id=category_id,
                    type_name=subcategory
                ))
        
        bulk_insert_objects(session, product_type_objects)
        
        logging.info(f"Successfully inserted {len(product_type_objects):,} product types!")
    except Exception as e:
        logging.error(f"Error inserting product types: {e}")
        raise

def insert_suppliers(session: Session):
    """Insert supplier data into the database from JSON file"""
    try:
        logging.info(f"Loading suppliers from {SUPPLIER_DATA_FILE}...")
        
        supplier_json_path = os.path.join(os.path.dirname(__file__), REFERENCE_DATA_DIR, SUPPLIER_DATA_FILE)
        
        if not os.path.exists(supplier_json_path):
            raise FileNotFoundError(f"Supplier data file not found: {supplier_json_path}")
        
        with open(supplier_json_path, 'r') as f:
            supplier_config = json.load(f)
        
        if 'suppliers' in supplier_config:
            suppliers_from_json = supplier_config['suppliers']
        else:
            suppliers_from_json = [supplier_config[key] for key in supplier_config.keys() if key.isdigit()]
        
        if not suppliers_from_json:
            raise ValueError(f"No suppliers found in {SUPPLIER_DATA_FILE}")
        
        logging.info(f"Loaded {len(suppliers_from_json)} suppliers from JSON file")
        
        supplier_objects = []
        for idx, supplier in enumerate(suppliers_from_json, 1):
            supplier_code = supplier.get('supplier_code', f"SUP{idx:03d}")
            
            address = supplier.get('address', '')
            address_parts = address.split(',') if address else []
            
            address_line1 = address_parts[0].strip() if len(address_parts) > 0 else ''
            city = address_parts[1].strip() if len(address_parts) > 1 else 'Seattle'
            
            if len(address_parts) > 2:
                state_postal = address_parts[2].strip().split()
                state = state_postal[0] if len(state_postal) > 0 else 'WA'
                postal_code = state_postal[1] if len(state_postal) > 1 else '98000'
            else:
                state = 'WA'
                postal_code = '98000'
            
            # Get minimum order amount from JSON, or use default
            min_order = supplier.get('min_order_amount', 500.00)
            bulk_threshold = min_order * 5
            bulk_discount = random.uniform(5.0, 10.0)
            
            # Get rating from JSON, or use default
            rating = supplier.get('rating', 4.0)
            
            # Get ESG compliance from JSON, with fallback logic
            esg_compliant = supplier.get('esg_compliant', rating >= 4.0)
            
            # Get preferred vendor status from JSON, with fallback logic
            is_preferred = supplier.get('preferred_vendor', rating >= 4.5)
            
            # Get approved vendor status from JSON, with fallback logic
            is_approved = supplier.get('approved_vendor', rating >= 3.5)
            
            supplier_id = supplier.get('supplier_id', idx)
            
            # Get payment terms from contract if available, otherwise from supplier
            payment_terms = supplier.get('payment_terms', 'Net 30')
            if 'contracts' in supplier and len(supplier['contracts']) > 0:
                payment_terms = supplier['contracts'][0].get('payment_terms', payment_terms)
            
            supplier_objects.append(Supplier(
                supplier_id=supplier_id,
                supplier_name=supplier.get('supplier_name', supplier.get('name', f'Supplier {idx}')),
                supplier_code=supplier_code,
                contact_email=supplier.get('contact_email', supplier.get('email', f'contact{idx}@supplier.com')),
                contact_phone=supplier.get('contact_phone', supplier.get('phone', f'(555) {idx:03d}-0000')),
                address_line1=address_line1,
                address_line2='',
                city=city,
                state_province=state,
                postal_code=postal_code,
                country='USA',
                payment_terms=payment_terms,
                lead_time_days=supplier.get('lead_time_days', 14),
                minimum_order_amount=min_order,
                bulk_discount_threshold=bulk_threshold,
                bulk_discount_percent=bulk_discount,
                supplier_rating=rating,
                esg_compliant=esg_compliant,
                approved_vendor=is_approved,
                preferred_vendor=is_preferred
            ))
        
        logging.info(f"Prepared {len(supplier_objects)} suppliers for insertion...")
        
        bulk_insert_objects(session, supplier_objects)
        
        logging.info(f"Successfully inserted {len(supplier_objects):,} suppliers!")
        
        # Store category and product type mappings
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
        
        suppliers_in_db = session.query(Supplier).all()
        
        performance_objects = []
        for supplier_obj in suppliers_in_db:
            for months_ago in range(0, random.randint(3, 7)):
                evaluation_date = date.today().replace(day=1) - timedelta(days=months_ago * 30)
                
                base_cost_score = random.uniform(3.5, 4.8)
                base_quality_score = random.uniform(3.2, 4.9)
                base_delivery_score = random.uniform(3.0, 4.7)
                base_compliance_score = random.uniform(4.2, 5.0)
                
                cost_score = max(1.0, min(5.0, base_cost_score + random.uniform(-0.3, 0.3)))
                quality_score = max(1.0, min(5.0, base_quality_score + random.uniform(-0.4, 0.4)))
                delivery_score = max(1.0, min(5.0, base_delivery_score + random.uniform(-0.5, 0.5)))
                compliance_score = max(1.0, min(5.0, base_compliance_score + random.uniform(-0.2, 0.2)))
                
                overall_score = (cost_score * 0.3 + quality_score * 0.3 + delivery_score * 0.25 + compliance_score * 0.15)
                
                performance_objects.append(SupplierPerformance(
                    supplier_id=supplier_obj.supplier_id,
                    evaluation_date=evaluation_date,
                    cost_score=cost_score,
                    quality_score=quality_score,
                    delivery_score=delivery_score,
                    compliance_score=compliance_score,
                    overall_score=overall_score,
                    notes=f"Monthly evaluation for {supplier_obj.supplier_name}"
                ))
        
        bulk_insert_objects(session, performance_objects)
        
        logging.info(f"Successfully inserted {len(performance_objects):,} supplier performance evaluations!")
        
    except Exception as e:
        logging.error(f"Error inserting suppliers: {e}")
        raise

def insert_products(session: Session):
    """Insert product data into the database"""
    try:
        logging.info("Generating products...")
        
        # Get mappings
        categories_in_db = session.query(Category).all()
        category_mapping = {cat.category_name: cat.category_id for cat in categories_in_db}
        
        product_types_in_db = session.query(ProductType).all()
        type_mapping = {pt.type_name: (pt.type_id, pt.category_id) for pt in product_types_in_db}
        
        suppliers_in_db = session.query(Supplier).order_by(Supplier.preferred_vendor.desc(), Supplier.supplier_rating.desc()).all()
        
        if not suppliers_in_db:
            raise Exception("No suppliers found!")
        
        supplier_by_name = {s.supplier_name: s.supplier_id for s in suppliers_in_db}
        default_suppliers = suppliers_in_db[:5]
        
        product_objects = []
        sku_counter = 1000
        
        for main_category, subcategories in main_categories.items():
            category_id = category_mapping[main_category]
            
            for subcategory, products in subcategories.items():
                type_id, _ = type_mapping[subcategory]
                
                # Get suppliers for this category
                category_suppliers = SUPPLIER_CATEGORY_MAP.get(main_category, [])
                
                for product in products:
                    sku_counter += 1
                    sku = f"SKU{sku_counter}"
                    
                    # Find supplier
                    supplier_id = None
                    if category_suppliers:
                        supplier_name = random.choice(category_suppliers)
                        supplier_id = supplier_by_name.get(supplier_name)
                    
                    if not supplier_id:
                        supplier_id = random.choice(default_suppliers).supplier_id
                    
                    # Use the JSON price as the actual store selling price
                    json_price = product.get('price', 19.99)
                    base_price = round(float(json_price), 2)
                    
                    # Calculate cost for 33% gross margin
                    # Gross Margin = (Selling Price - Cost) / Selling Price = 0.33
                    # Therefore: Cost = Selling Price × (1 - 0.33) = Selling Price × 0.67
                    cost = round(base_price * 0.67, 2)
                    
                    # Extract image_url from product data (remove 'images/' prefix)
                    image_path = product.get('image_path', '')
                    image_url = image_path.replace('images/', '') if image_path else None
                    
                    product_objects.append(Product(
                        sku=sku,
                        product_name=product.get('name', f'Product {sku_counter}'),
                        category_id=category_id,
                        type_id=type_id,
                        supplier_id=supplier_id,
                        cost=cost,
                        base_price=base_price,
                        gross_margin_percent=33.00,
                        product_description=product.get('description', ''),
                        procurement_lead_time_days=random.randint(7, 30),
                        minimum_order_quantity=random.randint(1, 50),
                        discontinued=False,
                        image_url=image_url
                    ))
        
        bulk_insert_objects(session, product_objects)
        
        logging.info(f"Successfully inserted {len(product_objects):,} products!")
    except Exception as e:
        logging.error(f"Error inserting products: {e}")
        raise

def insert_customers(session: Session, num_customers: int = 20000):
    """Insert customer data into the database"""
    try:
        logging.info(f"Generating {num_customers:,} customers...")
        
        stores_in_db = session.query(Store).all()
        store_ids = [s.store_id for s in stores_in_db]
        store_name_to_id = {s.store_name: s.store_id for s in stores_in_db}
        
        if not store_ids:
            raise Exception("No stores found! Please insert stores first.")
        
        customer_objects = []
        
        for i in range(1, num_customers + 1):
            first_name = fake.first_name().replace("'", "")
            last_name = fake.last_name().replace("'", "")
            email = f"{first_name.lower()}.{last_name.lower()}.{i}@example.com"
            phone = generate_phone_number()
            
            preferred_store_name = weighted_store_choice()
            primary_store_id = store_name_to_id.get(preferred_store_name)
            
            if primary_store_id is None:
                primary_store_id = stores_in_db[0].store_id
            
            customer_objects.append(Customer(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                primary_store_id=primary_store_id
            ))
        
        bulk_insert_objects(session, customer_objects)
        
        # Log customer distribution by store
        distribution = session.query(
            Store.store_name,
            func.count(Customer.customer_id).label('customer_count')
        ).outerjoin(Customer, Store.store_id == Customer.primary_store_id)\
         .group_by(Store.store_id, Store.store_name)\
         .order_by(func.count(Customer.customer_id).desc())\
         .all()
        
        logging.info("Customer distribution by store:")
        for store_name, customer_count in distribution:
            percentage = (customer_count / num_customers * 100) if num_customers > 0 else 0
            logging.info(f"  {store_name}: {customer_count:,} customers ({percentage:.1f}%)")
        
        logging.info(f"Successfully inserted {num_customers:,} customers!")
    except Exception as e:
        logging.error(f"Error inserting customers: {e}")
        raise

def insert_orders_and_items(session: Session, num_orders: int = 50000):
    """Insert order and order item data"""
    try:
        logging.info(f"Generating {num_orders:,} orders and order items...")
        
        # Get sample customers (we'll reuse some)
        customer_ids = [c.customer_id for c in session.query(Customer.customer_id).order_by(func.random()).limit(num_orders * 2).all()]
        
        if not customer_ids:
            raise Exception("No customers found!")
        
        store_ids = [s.store_id for s in session.query(Store.store_id).all()]
        
        products = session.query(Product.product_id, Product.base_price).all()
        product_list = [(p.product_id, p.base_price) for p in products]
        
        order_objects = []
        order_item_objects = []
        
        for i in range(num_orders):
            customer_id = random.choice(customer_ids)
            store_id = random.choice(store_ids)
            order_date = date.today() - timedelta(days=random.randint(0, 365))
            
            order = Order(
                customer_id=customer_id,
                store_id=store_id,
                order_date=order_date
            )
            order_objects.append(order)
        
        # Insert orders first to get IDs
        bulk_insert_objects(session, order_objects)
        
        # Get the inserted order IDs
        order_ids = [o.order_id for o in session.query(Order.order_id).order_by(Order.order_id.desc()).limit(num_orders).all()]
        order_ids.reverse()
        
        # Now create order items
        for order_id in order_ids:
            store_id = random.choice(store_ids)
            
            # Add 1-5 items per order
            num_items = random.randint(1, 5)
            for _ in range(num_items):
                product_id, base_price = random.choice(product_list)
                quantity = random.randint(1, 10)
                unit_price = float(base_price)
                discount_percent = random.choice([0, 0, 0, 5, 10, 15])
                discount_amount = round((unit_price * quantity * discount_percent) / 100, 2)
                total_amount = round((unit_price * quantity) - discount_amount, 2)
                
                order_item_objects.append(OrderItem(
                    order_id=order_id,
                    store_id=store_id,
                    product_id=product_id,
                    quantity=quantity,
                    unit_price=unit_price,
                    discount_percent=discount_percent,
                    discount_amount=discount_amount,
                    total_amount=total_amount
                ))
        
        bulk_insert_objects(session, order_item_objects)
        
        # Insert inventory data (stock levels for products at stores)
        # Each store carries about 30 products with 10-20 units in stock
        stores_in_db = session.query(Store).all()
        products_in_db = session.query(Product).all()
        
        inventory_objects = []
        for store in stores_in_db:
            # Each store carries approximately 30 products (random selection)
            num_products_per_store = min(30, len(products_in_db))
            selected_products = random.sample(products_in_db, num_products_per_store)
            
            for product in selected_products:
                # Stock levels between 0 and 20 items
                stock_level = random.randint(0, 20)
                inventory_objects.append(Inventory(
                    store_id=store.store_id,
                    product_id=product.product_id,
                    stock_level=stock_level
                ))
        
        bulk_insert_objects(session, inventory_objects)
        
        logging.info(f"Successfully inserted {len(order_objects):,} orders!")
        logging.info(f"Successfully inserted {len(order_item_objects):,} order items!")
        logging.info(f"Successfully inserted {len(inventory_objects):,} inventory records!")
        
    except Exception as e:
        logging.error(f"Error inserting orders: {e}")
        raise

def insert_agent_support_data(session: Session):
    """Insert agent support data (approvers, contracts, policies, procurement requests, notifications)"""
    try:
        logging.info("Generating essential agent support data...")
        
        # Generate approvers
        approver_objects = [
            Approver(employee_id="EXEC001", full_name="Jane CEO", email="jane.ceo@company.com", 
                    department="Management", approval_limit=1000000, is_active=True),
            Approver(employee_id="DIR001", full_name="John Finance Director", email="john.director@company.com",
                    department="Finance", approval_limit=250000, is_active=True),
            Approver(employee_id="DIR002", full_name="Sarah Operations Director", email="sarah.ops@company.com",
                    department="Operations", approval_limit=200000, is_active=True),
            Approver(employee_id="MGR001", full_name="Mike Procurement Manager", email="mike.proc@company.com",
                    department="Procurement", approval_limit=50000, is_active=True),
            Approver(employee_id="MGR002", full_name="Lisa Finance Manager", email="lisa.fin@company.com",
                    department="Finance", approval_limit=25000, is_active=True),
            Approver(employee_id="SUP001", full_name="Tom Operations Supervisor", email="tom.ops@company.com",
                    department="Operations", approval_limit=10000, is_active=True),
            Approver(employee_id="SUP002", full_name="Amy Procurement Specialist", email="amy.proc@company.com",
                    department="Procurement", approval_limit=5000, is_active=True)
        ]
        
        bulk_insert_objects(session, approver_objects)
        
        # Generate supplier contracts
        suppliers_in_db = session.query(Supplier).all()
        
        contract_objects = []
        for i, supplier in enumerate(suppliers_in_db, 1):
            end_date = date(2025, 12, 31)
            contract_value = round(random.uniform(50000, 500000), 2)
            contract_objects.append(SupplierContract(
                supplier_id=supplier.supplier_id,
                contract_number=f"CON-2024-{i:03d}",
                contract_status="active",
                start_date=date(2024, 1, 1),
                end_date=end_date,
                contract_value=contract_value,
                payment_terms="Net 30",
                auto_renew=random.choice([True, False])
            ))
        
        bulk_insert_objects(session, contract_objects)
        
        # Generate company policies
        policy_objects = [
            CompanyPolicy(policy_name="Procurement Policy", policy_type="procurement",
                         policy_content="All purchases over $5,000 require manager approval. Competitive bidding required for orders over $25,000.",
                         department="Procurement", minimum_order_threshold=5000, approval_required=True),
            CompanyPolicy(policy_name="Order Processing Policy", policy_type="order_processing",
                         policy_content="Orders processed within 24 hours. Rush orders require $50 fee and manager approval.",
                         department="Operations", approval_required=False),
            CompanyPolicy(policy_name="Budget Authorization", policy_type="budget_authorization",
                         policy_content="Spending limits: Manager $50K, Director $250K, Executive $1M+",
                         department="Finance", approval_required=True),
            CompanyPolicy(policy_name="Vendor Approval", policy_type="vendor_approval",
                         policy_content="All new vendors require approval and background check completion.",
                         department="Procurement", approval_required=True)
        ]
        
        bulk_insert_objects(session, policy_objects)
        
        # Generate procurement requests
        products_sample = session.query(Product).limit(20).all()
        departments = ["Operations", "Finance", "Procurement", "Management"]
        urgency_levels = ["Low", "Normal", "High", "Critical"]
        approval_statuses = ["Pending", "Approved", "Rejected"]
        
        procurement_objects = []
        for i in range(25):
            if not products_sample:
                break
            
            product = random.choice(products_sample)
            unit_cost = float(product.cost)
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
                approved_by = random.choice([a.employee_id for a in approver_objects])
                approved_at = request_date + timedelta(days=random.randint(1, 5))
            
            procurement_objects.append(ProcurementRequest(
                request_number=request_number,
                requester_name=requester_name,
                requester_email=requester_email,
                department=department,
                product_id=product.product_id,
                supplier_id=product.supplier_id,
                quantity_requested=quantity_requested,
                unit_cost=unit_cost,
                total_cost=total_cost,
                justification=justification,
                urgency_level=urgency_level,
                approval_status=approval_status,
                approved_by=approved_by,
                approved_at=approved_at,
                required_by_date=required_by_date
            ))
        
        if procurement_objects:
            bulk_insert_objects(session, procurement_objects)
        
        # Generate notifications
        recent_requests = session.query(ProcurementRequest)\
            .order_by(ProcurementRequest.request_date.desc())\
            .limit(10)\
            .all()
        
        notification_objects = []
        for request in recent_requests:
            notification_type = "approval_request" if request.approval_status == "Pending" else "status_update"
            subject = f"Procurement Request {request.request_id}: {request.approval_status}"
            message = f"Your procurement request for ${request.total_cost:.2f} has been {request.approval_status.lower()}."
            
            notification_objects.append(Notification(
                request_id=request.request_id,
                notification_type=notification_type,
                recipient_email=request.requester_email,
                subject=subject,
                message=message
            ))
        
        if notification_objects:
            bulk_insert_objects(session, notification_objects)
        
        logging.info(f"Successfully inserted {len(approver_objects)} approvers!")
        logging.info(f"Successfully inserted {len(contract_objects)} supplier contracts!")
        logging.info(f"Successfully inserted {len(policy_objects)} company policies!")
        logging.info(f"Successfully inserted {len(procurement_objects)} procurement requests!")
        logging.info(f"Successfully inserted {len(notification_objects)} notifications!")
        
    except Exception as e:
        logging.error(f"Error inserting agent support data: {e}")
        raise

def show_statistics(session: Session):
    """Display comprehensive database statistics"""
    try:
        # Basic table counts
        stats = {
            'stores': session.query(func.count(Store.store_id)).scalar(),
            'categories': session.query(func.count(Category.category_id)).scalar(),
            'product_types': session.query(func.count(ProductType.type_id)).scalar(),
            'products': session.query(func.count(Product.product_id)).scalar(),
            'suppliers': session.query(func.count(Supplier.supplier_id)).scalar(),
            'customers': session.query(func.count(Customer.customer_id)).scalar(),
            'orders': session.query(func.count(Order.order_id)).scalar(),
            'order_items': session.query(func.count(OrderItem.order_item_id)).scalar(),
            'inventory': session.query(func.count(Inventory.store_id)).scalar(),
            'approvers': session.query(func.count(Approver.approver_id)).scalar(),
            'supplier_contracts': session.query(func.count(SupplierContract.contract_id)).scalar(),
            'supplier_performance': session.query(func.count(SupplierPerformance.performance_id)).scalar(),
            'company_policies': session.query(func.count(CompanyPolicy.policy_id)).scalar(),
            'procurement_requests': session.query(func.count(ProcurementRequest.request_id)).scalar(),
            'notifications': session.query(func.count(Notification.notification_id)).scalar(),
        }
        
        logging.info("=" * 70)
        logging.info("📊 DATABASE STATISTICS & ANALYTICS")
        logging.info("=" * 70)
        
        # Table counts
        logging.info("\n📋 TABLE COUNTS:")
        logging.info("-" * 70)
        for table, count in stats.items():
            logging.info(f"  {table:.<45} {count:>15,}")
        
        total_records = sum(stats.values())
        logging.info("-" * 70)
        logging.info(f"  {'TOTAL RECORDS':.<45} {total_records:>15,}")
        
        # Order statistics
        logging.info("\n💰 ORDER STATISTICS:")
        logging.info("-" * 70)
        
        order_stats = session.query(
            func.count(func.distinct(Order.order_id)).label('total_orders'),
            func.sum(OrderItem.total_amount).label('total_revenue'),
            func.avg(OrderItem.total_amount).label('avg_item_value'),
            func.min(OrderItem.total_amount).label('min_item'),
            func.max(OrderItem.total_amount).label('max_item'),
            func.count(func.distinct(Order.customer_id)).label('unique_customers')
        ).outerjoin(OrderItem, Order.order_id == OrderItem.order_id).first()
        
        if order_stats.total_orders and order_stats.total_orders > 0:
            logging.info(f"  {'Total Orders':.<45} {order_stats.total_orders:>15,}")
            logging.info(f"  {'Total Revenue':.<45} ${float(order_stats.total_revenue or 0):>14,.2f}")
            logging.info(f"  {'Average Item Value':.<45} ${float(order_stats.avg_item_value or 0):>14,.2f}")
            logging.info(f"  {'Min Item Value':.<45} ${float(order_stats.min_item or 0):>14,.2f}")
            logging.info(f"  {'Max Item Value':.<45} ${float(order_stats.max_item or 0):>14,.2f}")
            logging.info(f"  {'Unique Customers':.<45} {order_stats.unique_customers:>15,}")
        
        # Customer statistics
        logging.info("\n👥 CUSTOMER STATISTICS:")
        logging.info("-" * 70)
        
        total_custs = stats['customers']
        stores_count = stats['stores']
        avg_per_store = total_custs / stores_count if stores_count > 0 else 0
        
        logging.info(f"  {'Total Customers':.<45} {total_custs:>15,}")
        logging.info(f"  {'Stores Represented':.<45} {stores_count:>15,}")
        logging.info(f"  {'Average Per Store':.<45} {avg_per_store:>15,.0f}")
        
        # Top stores by customer count
        logging.info("\n🏪 TOP STORES BY CUSTOMERS:")
        logging.info("-" * 70)
        
        top_stores = session.query(
            Store.store_name,
            func.count(Customer.customer_id).label('customer_count')
        ).outerjoin(Customer, Store.store_id == Customer.primary_store_id)\
         .group_by(Store.store_id)\
         .order_by(func.count(Customer.customer_id).desc())\
         .limit(5)\
         .all()
        
        for store_name, count in top_stores:
            pct = (count / total_custs * 100) if total_custs > 0 else 0
            logging.info(f"  {store_name:.<45} {count:>10,} ({pct:>5.1f}%)")
        
        # Product category distribution
        logging.info("\n📦 PRODUCT CATEGORY DISTRIBUTION:")
        logging.info("-" * 70)
        
        categories = session.query(
            Category.category_name,
            func.count(Product.product_id).label('product_count')
        ).outerjoin(Product, Category.category_id == Product.category_id)\
         .group_by(Category.category_id)\
         .order_by(func.count(Product.product_id).desc())\
         .all()
        
        for cat_name, count in categories:
            pct = (count / stats['products'] * 100) if stats['products'] > 0 else 0
            logging.info(f"  {cat_name:.<45} {count:>10,} ({pct:>5.1f}%)")
        
        # Supplier performance
        logging.info("\n⭐ SUPPLIER PERFORMANCE METRICS:")
        logging.info("-" * 70)
        
        supplier_metrics = session.query(
            func.avg(Supplier.supplier_rating).label('avg_rating'),
            func.count(func.distinct(Supplier.supplier_id)).label('total_suppliers'),
            func.avg(Supplier.lead_time_days).label('avg_lead_time'),
            func.count(func.distinct(SupplierPerformance.performance_id)).label('total_evaluations')
        ).outerjoin(SupplierPerformance, Supplier.supplier_id == SupplierPerformance.supplier_id).first()
        
        if supplier_metrics.total_suppliers and supplier_metrics.total_suppliers > 0:
            logging.info(f"  {'Average Supplier Rating':.<45} {float(supplier_metrics.avg_rating or 0):>15.2f}⭐")
            logging.info(f"  {'Total Suppliers':.<45} {supplier_metrics.total_suppliers:>15,}")
            logging.info(f"  {'Average Lead Time':.<45} {float(supplier_metrics.avg_lead_time or 0):>14.1f} days")
            logging.info(f"  {'Performance Evaluations':.<45} {supplier_metrics.total_evaluations:>15,}")
        
        # Inventory statistics
        logging.info("\n📊 INVENTORY STATISTICS:")
        logging.info("-" * 70)
        
        inv_stats = session.query(
            func.count(Inventory.store_id).label('total_records'),
            func.avg(Inventory.stock_level).label('avg_stock'),
            func.sum(Inventory.stock_level).label('total_stock'),
            func.min(Inventory.stock_level).label('min_stock'),
            func.max(Inventory.stock_level).label('max_stock')
        ).first()
        
        if inv_stats.total_records and inv_stats.total_records > 0:
            logging.info(f"  {'Inventory Records':.<45} {inv_stats.total_records:>15,}")
            logging.info(f"  {'Total Units in Stock':.<45} {inv_stats.total_stock:>15,.0f}")
            logging.info(f"  {'Average Stock per Location':.<45} {float(inv_stats.avg_stock or 0):>15.1f}")
            logging.info(f"  {'Min Stock Level':.<45} {inv_stats.min_stock:>15,}")
            logging.info(f"  {'Max Stock Level':.<45} {inv_stats.max_stock:>15,}")
        
        # Store inventory details
        logging.info("\n🏬 INVENTORY BY STORE:")
        logging.info("-" * 70)
        
        store_inventory = session.query(
            Store.store_name,
            func.count(Inventory.product_id).label('num_products'),
            func.sum(Inventory.stock_level).label('total_stock'),
            func.avg(Inventory.stock_level).label('avg_stock'),
            func.min(Inventory.stock_level).label('min_stock'),
            func.max(Inventory.stock_level).label('max_stock')
        ).join(Inventory, Store.store_id == Inventory.store_id)\
         .group_by(Store.store_id, Store.store_name)\
         .order_by(Store.store_name)\
         .all()
        
        for store_name, num_products, total_stock, avg_stock, min_stock, max_stock in store_inventory:
            logging.info(f"  {store_name[:40]:.<40}")
            logging.info(f"    Products: {num_products:>3} | Total Stock: {total_stock:>4} | Avg: {float(avg_stock):>5.1f} | Range: {min_stock}-{max_stock}")
        
        logging.info("\n" + "=" * 70)
        
    except Exception as e:
        logging.error(f"Error retrieving statistics: {e}")

def main():
    """Main function to orchestrate database generation"""
    try:
        logging.info("Starting SQLite database generation with SQLAlchemy ORM...")
        
        # Create engine and session
        engine, SessionLocal = create_engine_and_session()
        
        # Create schema
        create_database_schema(engine)
        
        # Create a session for data insertion
        session = SessionLocal()
        
        try:
            # Insert reference data
            insert_stores(session)
            insert_categories(session)
            insert_product_types(session)
            insert_suppliers(session)
            insert_products(session)
            
            # Insert transactional data
            insert_customers(session, num_customers=20000)
            insert_orders_and_items(session, num_orders=50000)
            
            # Insert agent support data
            insert_agent_support_data(session)
            
            # Show statistics
            show_statistics(session)
            
            logging.info("✅ Database generation completed successfully!")
            
        finally:
            session.close()
            logging.info(f"Session closed for {SQLITE_DB_FILE}.")
            
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    main()
