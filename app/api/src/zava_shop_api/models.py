from pydantic import BaseModel, Field
from typing import Optional, List

# Pydantic models for API responses
class Product(BaseModel):
    """Product model for API responses"""
    product_id: int = Field(..., description="Unique product identifier")
    sku: str = Field(..., description="Stock keeping unit")
    product_name: str = Field(..., description="Product display name")
    category_name: str = Field(..., description="Product category")
    type_name: str = Field(..., description="Product type")
    unit_price: float = Field(..., description="Retail price")
    cost: float = Field(..., description="Product cost")
    gross_margin_percent: float = Field(..., description="Profit margin percentage")
    product_description: Optional[str] = Field(None, description="Product description")
    supplier_name: Optional[str] = Field(None, description="Supplier name")
    discontinued: bool = Field(False, description="Product availability status")
    image_url: Optional[str] = Field(None, description="Product image URL")


class ProductList(BaseModel):
    """List of products response"""
    products: List[Product]
    total: int


class Store(BaseModel):
    """Store location model for API responses"""
    id: int = Field(..., description="Unique store identifier")
    name: str = Field(..., description="Store name")
    location: str = Field(..., description="Store location/address")
    is_online: bool = Field(..., description="Whether this is an online store")
    location_key: str = Field(..., description="Location key for image mapping")
    products: int = Field(..., description="Number of products in stock")
    total_stock: int = Field(..., description="Total stock level across products")
    inventory_value: float = Field(..., description="Total inventory retail value")
    status: str = Field(..., description="Store status (Open/Online)")
    hours: str = Field(..., description="Store operating hours")


class StoreList(BaseModel):
    """List of stores response"""
    stores: List[Store]
    total: int


class Category(BaseModel):
    """Category model for API responses"""
    id: int = Field(..., description="Unique category identifier")
    name: str = Field(..., description="Category name")


class CategoryList(BaseModel):
    """List of categories response"""
    categories: List[Category]
    total: int


class TopCategory(BaseModel):
    """Top category model for dashboard analytics"""
    name: str = Field(..., description="Category name")
    revenue: float = Field(..., description="Total retail value of inventory")
    percentage: float = Field(..., description="Percentage relative to top category")
    product_count: int = Field(..., description="Number of distinct products")
    total_stock: int = Field(..., description="Total stock level across products")
    cost_value: float = Field(..., description="Total cost value of inventory")
    potential_profit: float = Field(..., description="Potential profit if all sold")


class TopCategoryList(BaseModel):
    """List of top categories response"""
    categories: List[TopCategory]
    total: int = Field(..., description="Number of categories returned")
    max_value: float = Field(..., description="Maximum revenue value for percentage calculation")


class Supplier(BaseModel):
    """Supplier model for management interface"""
    id: int = Field(..., description="Unique supplier identifier")
    name: str = Field(..., description="Supplier name")
    code: str = Field(..., description="Supplier code")
    location: str = Field(..., description="Supplier location (city, state)")
    contact: str = Field(..., description="Contact email address")
    phone: str = Field(..., description="Contact phone number")
    rating: float = Field(..., description="Supplier rating (0.0 to 5.0)")
    esg_compliant: bool = Field(..., description="ESG compliance status")
    approved: bool = Field(..., description="Approved vendor status")
    preferred: bool = Field(..., description="Preferred vendor status")
    categories: List[str] = Field(..., description="Product categories supplied")
    lead_time: int = Field(..., description="Lead time in days")
    payment_terms: str = Field(..., description="Payment terms")
    min_order: float = Field(..., description="Minimum order amount")
    bulk_discount: float = Field(..., description="Bulk discount percentage")


class SupplierList(BaseModel):
    """List of suppliers response"""
    suppliers: List[Supplier]
    total: int = Field(..., description="Total number of suppliers")


class InventoryItem(BaseModel):
    """Inventory item model for management interface"""
    store_id: int = Field(..., description="Store identifier")
    store_name: str = Field(..., description="Store name")
    store_location: str = Field(..., description="Store location description")
    is_online: bool = Field(..., description="Whether this is an online store")
    product_id: int = Field(..., description="Product identifier")
    product_name: str = Field(..., description="Product name")
    sku: str = Field(..., description="Product SKU")
    category: str = Field(..., description="Product category")
    type: str = Field(..., description="Product type")
    stock_level: int = Field(..., description="Current stock level")
    reorder_point: int = Field(..., description="Reorder threshold")
    is_low_stock: bool = Field(..., description="Whether stock is below reorder point")
    unit_cost: float = Field(..., description="Unit cost")
    unit_price: float = Field(..., description="Unit retail price")
    stock_value: float = Field(..., description="Total cost value of stock")
    retail_value: float = Field(..., description="Total retail value of stock")
    supplier_name: Optional[str] = Field(None, description="Supplier name")
    supplier_code: Optional[str] = Field(None, description="Supplier code")
    lead_time: Optional[int] = Field(None, description="Lead time in days")
    image_url: Optional[str] = Field(None, description="Product image URL")


class InventorySummary(BaseModel):
    """Inventory summary statistics"""
    total_items: int = Field(..., description="Total number of inventory items")
    low_stock_count: int = Field(..., description="Number of low stock items")
    total_stock_value: float = Field(..., description="Total cost value of all stock")
    total_retail_value: float = Field(..., description="Total retail value of all stock")
    avg_stock_level: float = Field(..., description="Average stock level per item")


class InventoryResponse(BaseModel):
    """Inventory response with items and summary"""
    inventory: List[InventoryItem]
    summary: InventorySummary


class ManagementProduct(BaseModel):
    """Model for product information in management interface with inventory details."""
    product_id: int = Field(..., description="Unique product identifier")
    sku: str = Field(..., description="Stock Keeping Unit identifier")
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(None, description="Product description")
    category: str = Field(..., description="Product category name")
    type: str = Field(..., description="Product type name")
    base_price: float = Field(..., description="Base retail price")
    cost: float = Field(..., description="Cost per unit")
    margin: float = Field(..., description="Gross margin percentage")
    discontinued: bool = Field(..., description="Whether product is discontinued")
    supplier_id: Optional[int] = Field(None, description="Supplier identifier")
    supplier_name: Optional[str] = Field(None, description="Supplier name")
    supplier_code: Optional[str] = Field(None, description="Supplier code")
    lead_time: Optional[int] = Field(None, description="Lead time in days")
    total_stock: int = Field(..., description="Total stock across all stores")
    store_count: int = Field(..., description="Number of stores carrying this product")
    stock_value: float = Field(..., description="Total inventory value at cost")
    retail_value: float = Field(..., description="Total inventory value at retail price")
    image_url: Optional[str] = Field(None, description="Product image URL")


class ProductPagination(BaseModel):
    """Pagination information for product list."""
    total: int = Field(..., description="Total number of products matching criteria")
    limit: int = Field(..., description="Maximum number of products per page")
    offset: int = Field(..., description="Current offset in results")
    has_more: bool = Field(..., description="Whether more products are available")


class ManagementProductResponse(BaseModel):
    """Response model for management products list with pagination."""
    products: List[ManagementProduct] = Field(..., description="List of products")
    pagination: ProductPagination = Field(..., description="Pagination information")


# Authentication models
class LoginRequest(BaseModel):
    """Login request model"""
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str = Field(..., description="Bearer token for API access")
    token_type: str = Field(default="bearer", description="Token type")
    user_role: str = Field(..., description="User role (admin or store_manager)")
    store_id: Optional[int] = Field(None, description="Store ID for store managers")
    store_name: Optional[str] = Field(None, description="Store name for store managers")
    name: Optional[str] = Field(None, description="Full name of the user")


class TokenData(BaseModel):
    """Token data model for internal use"""
    username: str
    user_role: str
    store_id: Optional[int] = None
    customer_id: Optional[int] = None


class InsightAction(BaseModel):
    """Action button for an insight"""
    label: str = Field(..., description="Button label text")
    type: str = Field(
        ..., description="Action type: 'product-search', 'navigation', or 'workflow-trigger'"
    )
    query: Optional[str] = Field(
        None, description="Search query for product-search type"
    )
    path: Optional[str] = Field(
        None, description="Navigation path for navigation type"
    )
    workflow_message: Optional[str] = Field(
        None, description="Message to send to workflow for workflow-trigger type"
    )
    instructions: Optional[str] = Field(
        None, description="Instructions to pre-fill in the AI agent interface"
    )


class Insight(BaseModel):
    """Individual AI-generated insight"""
    type: str = Field(..., description="Insight type: 'success', 'warning', or 'info'")
    title: str = Field(..., description="Insight title/heading")
    description: str = Field(..., description="Detailed insight description")
    action: Optional[InsightAction] = Field(None, description="Optional action button")


class WeeklyInsights(BaseModel):
    """Weekly AI insights response"""
    summary: str = Field(..., description="AI-generated insights disclaimer (shown in italics)")
    weather_summary: str = Field(..., description="Summary of weather conditions")
    events_summary: Optional[str] = Field(None, description="Summary of local events")
    stock_items: List[str] = Field(
        default_factory=list,
        description="List of specific product items to stock up on (determined by stock agent)",
    )
    insights: List[Insight] = Field(..., description="List of specific insights")
    unified_action: Optional[InsightAction] = Field(
        None,
        description="Single unified action that combines all insights for comprehensive analysis",
    )


class CacheInvalidationResponse(BaseModel):
    """Response for cache invalidation operations"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message about the operation")
    store_id: Optional[int] = Field(None, description="Store ID if invalidating specific store")
    count: Optional[int] = Field(None, description="Number of caches invalidated if invalidating all")


class CacheInfo(BaseModel):
    """Cache metadata information"""
    store_id: int = Field(..., description="Store identifier")
    generated_date: str = Field(..., description="ISO date when cache was generated")
    filename: str = Field(..., description="Cache filename")
    is_valid: bool = Field(..., description="Whether cache is still valid")
    age_days: int = Field(..., description="Age of cache in days")
    age_hours: int = Field(..., description="Additional hours beyond full days")


class CacheInfoResponse(BaseModel):
    """Response for cache info queries"""
    success: bool = Field(..., description="Whether the operation was successful")
    cache_info: Optional[CacheInfo] = Field(None, description="Cache information if found")
    message: Optional[str] = Field(None, description="Error message if cache not found")
    store_id: Optional[int] = Field(None, description="Store ID queried")


# Order models for customer API
class OrderItemResponse(BaseModel):
    """Order item in a customer order"""
    order_item_id: int = Field(..., description="Order item identifier")
    product_id: int = Field(..., description="Product identifier")
    product_name: str = Field(..., description="Product name")
    sku: str = Field(..., description="Product SKU")
    quantity: int = Field(..., description="Quantity ordered")
    unit_price: float = Field(..., description="Unit price at time of order")
    discount_percent: int = Field(..., description="Discount percentage applied")
    discount_amount: float = Field(..., description="Discount amount")
    total_amount: float = Field(..., description="Total amount for this line item")
    image_url: Optional[str] = Field(None, description="Product image URL")


class OrderResponse(BaseModel):
    """Customer order response"""
    order_id: int = Field(..., description="Order identifier")
    order_date: str = Field(..., description="Order date (YYYY-MM-DD)")
    store_id: int = Field(..., description="Store identifier")
    store_name: str = Field(..., description="Store name")
    items: List[OrderItemResponse] = Field(..., description="Order items")
    total_items: int = Field(..., description="Total number of items")
    order_total: float = Field(..., description="Total order amount")


class OrderListResponse(BaseModel):
    """List of customer orders"""
    orders: List[OrderResponse] = Field(..., description="List of orders")
    total: int = Field(..., description="Total number of orders")


class CustomerProfile(BaseModel):
    """Customer profile information"""
    customer_id: int = Field(..., description="Customer identifier")
    first_name: str = Field(..., description="Customer first name")
    last_name: str = Field(..., description="Customer last name")
    email: str = Field(..., description="Customer email address")
    phone: Optional[str] = Field(None, description="Customer phone number")
    primary_store_id: Optional[int] = Field(None, description="Primary store ID")
    primary_store_name: Optional[str] = Field(None, description="Primary store name")


# Chat models for customer AI agent
class CustomerChatMessage(BaseModel):
    """Chat message for AI agent conversation"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class CustomerChatRequest(BaseModel):
    """Request to send message to AI agent"""
    message: str = Field(..., description="User's message to the AI agent")
    conversation_history: Optional[List[CustomerChatMessage]] = Field(
        default=[],
        description="Previous messages in the conversation"
    )


class CustomerChatResponse(BaseModel):
    """Response from AI agent"""
    message: str = Field(..., description="AI agent's response")
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation identifier for tracking"
    )
