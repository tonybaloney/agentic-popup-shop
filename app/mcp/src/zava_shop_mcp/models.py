# View models
from decimal import Decimal
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CompanyPolicyResult(BaseModel):
    policy_id: int
    policy_name: str
    policy_type: str
    policy_content: str
    department: Optional[str]
    minimum_order_threshold: Optional[Decimal]
    approval_required: bool
    is_active: bool
    policy_description: str
    content_length: int

class SupplierContractResult(BaseModel):
    supplier_name: str
    supplier_code: str
    contact_email: Optional[str]
    contact_phone: Optional[str]
    contract_id: int
    contract_number: str
    contract_status: str
    start_date: datetime
    end_date: Optional[datetime]
    contract_value: Optional[Decimal]
    payment_terms: Optional[str]
    auto_renew: bool
    contract_created: datetime
    days_until_expiry: Optional[int]
    renewal_due_soon: bool

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
    contact_email: Optional[str]
    contact_phone: Optional[str]
    supplier_rating: float
    esg_compliant: bool
    preferred_vendor: bool
    approved_vendor: bool
    lead_time_days: int
    minimum_order_amount: Decimal
    bulk_discount_threshold: Optional[Decimal]
    bulk_discount_percent: Optional[Decimal]
    payment_terms: Optional[str]
    available_products: int
    avg_performance_score: float
    contract_status: Optional[str]
    contract_number: Optional[str]
    category_name: Optional[str]

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
    performance_notes: Optional[str]
    total_requests: int
    total_value: Decimal


class CompanySupplierPolicyResult(BaseModel):
    policy_id: int
    policy_name: str
    policy_type: str
    policy_content: str
    department: Optional[str]
    minimum_order_threshold: Optional[Decimal]
    approval_required: bool
    is_active: bool
    policy_description: str
    content_length: int
