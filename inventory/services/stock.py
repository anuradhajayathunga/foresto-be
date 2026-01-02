from django.db.models import Sum
from inventory.models import InventoryRecord


def get_current_stock(store, ingredient):
    return (
        InventoryRecord.objects
        .filter(store=store, ingredient=ingredient)
        .aggregate(total=Sum("quantity_on_hand"))["total"] or 0
    )
