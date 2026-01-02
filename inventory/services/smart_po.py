from django.db import transaction
from inventory.models import (
    PurchaseOrder,
    PurchaseOrderItem,
    MessageLog,
    Ingredient,
)

from inventory.services.stock import get_current_stock
from inventory.services.forecast import get_forecast_demand

SAFETY_BUFFER_RATIO = 0.20


def calculate_order_quantity(stock, demand, ingredient):
    required = demand - stock

    if required <= 0:
        return 0

    required *= (1 + SAFETY_BUFFER_RATIO)

    if ingredient.target_stock_level:
        required = max(required, ingredient.target_stock_level - stock)

    return round(required, 2)


@transaction.atomic
def generate_smart_po(store, ingredient, created_by=None, days=7):
    stock = get_current_stock(store, ingredient)
    demand = get_forecast_demand(store, ingredient, days)

    order_qty = calculate_order_quantity(stock, demand, ingredient)

    if order_qty <= 0:
        return None

    supplier = ingredient.default_supplier
    if not supplier:
        return None

    po = PurchaseOrder.objects.create(
        store=store,
        supplier=supplier,
        created_by=created_by,
        status="DRAFT",
        notes=f"Auto-generated PO for {ingredient.name}",
    )

    PurchaseOrderItem.objects.create(
        purchase_order=po,
        ingredient=ingredient,
        ordered_quantity=order_qty,
    )

    MessageLog.objects.create(
        purchase_order=po,
        supplier=supplier,
        channel="SYSTEM",
        recipient=supplier.email or supplier.phone or "N/A",
        message_body=(
            f"AUTO PO CREATED\n"
            f"PO#: {po.id}\n"
            f"Ingredient: {ingredient.name}\n"
            f"Quantity: {order_qty} {ingredient.unit_of_measure}"
        ),
        delivery_status="CREATED",
    )

    return po


def generate_batch_smart_pos(store, days=7, created_by=None):
    created_pos = []

    for ingredient in Ingredient.objects.all():
        po = generate_smart_po(
            store=store,
            ingredient=ingredient,
            created_by=created_by,
            days=days,
        )
        if po:
            created_pos.append(po)

    return created_pos
