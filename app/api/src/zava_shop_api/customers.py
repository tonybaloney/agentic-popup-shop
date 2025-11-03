

from zava_shop_api.models import OrderListResponse, OrderResponse, OrderItemResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)
from zava_shop_shared.models.sqlite.stores import Store as StoreModel
from zava_shop_shared.models.sqlite.products import Product as ProductModel
from zava_shop_shared.models.sqlite.orders import Order as OrderModel
from zava_shop_shared.models.sqlite.order_items import OrderItem as OrderItemModel
from logging import getLogger

logger = getLogger(__name__)

async def get_customer_orders(
    customer_id: int,
    session: AsyncSession
) -> OrderListResponse:
    """
    Endpoint to retrieve orders for the authenticated customer.
    """
    # Query orders for this customer
    stmt = (
        select(
            OrderModel.order_id,
            OrderModel.order_date,
            OrderModel.store_id,
            StoreModel.store_name,
        )
        .join(StoreModel, OrderModel.store_id == StoreModel.store_id)
        .where(OrderModel.customer_id == customer_id)
        .order_by(OrderModel.order_date.desc())
    )
    
    result = await session.execute(stmt)
    order_rows = result.all()
    
    if not order_rows:
        return OrderListResponse(orders=[], total=0)
    
    # For each order, get the order items
    orders = []
    for order_row in order_rows:
        # Query order items
        items_stmt = (
            select(
                OrderItemModel.order_item_id,
                OrderItemModel.product_id,
                ProductModel.product_name,
                ProductModel.sku,
                OrderItemModel.quantity,
                OrderItemModel.unit_price,
                OrderItemModel.discount_percent,
                OrderItemModel.discount_amount,
                OrderItemModel.total_amount,
                ProductModel.image_url
            )
            .join(
                ProductModel,
                OrderItemModel.product_id == ProductModel.product_id
            )
            .where(OrderItemModel.order_id == order_row.order_id)
        )
        
        items_result = await session.execute(items_stmt)
        item_rows = items_result.all()
        
        # Build order items list
        order_items = [
            OrderItemResponse(
                order_item_id=item.order_item_id,
                product_id=item.product_id,
                product_name=item.product_name,
                sku=item.sku,
                quantity=item.quantity,
                unit_price=float(item.unit_price),
                discount_percent=item.discount_percent,
                discount_amount=float(item.discount_amount),
                total_amount=float(item.total_amount),
                image_url=item.image_url
            )
            for item in item_rows
        ]
        
        # Calculate order totals
        total_items = sum(item.quantity for item in order_items)
        order_total = sum(item.total_amount for item in order_items)
        
        # Build order response
        order = OrderResponse(
            order_id=order_row.order_id,
            order_date=order_row.order_date.isoformat(),
            store_id=order_row.store_id,
            store_name=order_row.store_name,
            items=order_items,
            total_items=total_items,
            order_total=order_total
        )
        orders.append(order)
    
    return OrderListResponse(orders=orders, total=len(orders))