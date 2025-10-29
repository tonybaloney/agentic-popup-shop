# View models
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CompanyPolicyResult(BaseModel):
    policy_id: int
    policy_name: str
    policy_type: str
    policy_content: str
    department: Optional[str]
    minimum_order_threshold: Optional[float]
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
    contract_value: Optional[float]
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
    total_revenue: float
    avg_order_value: float
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
    cost: float
    base_price: float
    inventory_value: float
    retail_value: float
    low_stock_alert: bool

class StoreResult(BaseModel):
    store_id: int
    store_name: str
    is_online: bool
    rls_user_id: Optional[int]
