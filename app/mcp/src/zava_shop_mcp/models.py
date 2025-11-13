# View models
from decimal import Decimal
from pydantic import BaseModel
from datetime import datetime

class CompanyPolicyResult(BaseModel):
    policy_id: int
    policy_name: str
    policy_type: str
    policy_content: str
    department: str
    minimum_order_threshold: Decimal
    approval_required: bool
    is_active: bool
    policy_description: str
    content_length: int

class SupplierContractResult(BaseModel):
    supplier_name: str
    supplier_code: str
    contact_email: str
    contact_phone: str
    contract_id: int
    contract_number: str
    contract_status: str
    start_date: datetime
    end_date: datetime
    contract_value: Decimal
    payment_terms: str
    auto_renew: bool
    contract_created: datetime
    days_until_expiry: int = 0
    renewal_due_soon: bool = False

class SalesDataResult(BaseModel):
    month: str
    store_name: str
    is_online: bool
    category_name: str
    order_count: int
    total_revenue: Decimal
    avg_order_value: Decimal
    total_units_sold: int
    unique_customers: int

class TopProductSalesResult(BaseModel):
    product_name: str
    sku: str
    category_name: str
    order_count: int
    total_revenue: Decimal
    total_units_sold: int

class InventoryStatusResult(BaseModel):
    store_name: str
    is_online: bool
    product_name: str
    sku: str
    category_name: str
    product_type: str
    stock_level: int
    cost: Decimal
    base_price: Decimal
    inventory_value: Decimal
    retail_value: Decimal
    low_stock_alert: bool

class StoreResult(BaseModel):
    store_id: int
    store_name: str
    is_online: bool


class FindSuppliersResult(BaseModel):
    """Data model for supplier search results."""
    supplier_id: int
    supplier_name: str
    supplier_code: str
    contact_email: str
    contact_phone: str
    supplier_rating: float
    esg_compliant: bool
    preferred_vendor: bool
    approved_vendor: bool
    lead_time_days: int
    minimum_order_amount: Decimal
    bulk_discount_threshold: Decimal = 0 
    bulk_discount_percent: Decimal = 0
    payment_terms: str = ""
    available_products: int = 0
    avg_performance_score: float = 0.0
    contract_status: str = ""
    contract_number: str = ""
    category_name: str = ""

class SupplierHistoryAndPerformanceResult(BaseModel):
    supplier_name: str
    supplier_code: str
    supplier_rating: float
    esg_compliant: bool
    preferred_vendor: bool
    lead_time_days: int
    supplier_since: datetime
    evaluation_date: datetime
    cost_score: float
    quality_score: float
    delivery_score: float
    compliance_score: float
    overall_score: float
    performance_notes: str = ""
    total_requests: int = 0
    total_value: Decimal = Decimal(0)


class CompanySupplierPolicyResult(BaseModel):
    policy_id: int
    policy_name: str
    policy_type: str
    policy_content: str
    department: str
    minimum_order_threshold: Decimal = Decimal(0)
    approval_required: bool = False
    is_active: bool = False
    policy_description: str = ""
    content_length: int = 0


class StorePerformanceResult(BaseModel):
    """Store performance comparison data."""
    store_id: int
    store_name: str
    is_online: bool
    total_revenue: Decimal
    total_orders: int
    total_units_sold: int
    unique_customers: int
    avg_order_value: Decimal
    revenue_per_customer: Decimal
    efficiency_rank: int
