from decimal import Decimal
from django.conf import settings
from django.db import models


class InventoryItem(models.Model):
    class Unit(models.TextChoices):
        PCS = "PCS", "pcs"
        KG = "KG", "kg"
        G = "G", "g"
        L = "L", "l"
        ML = "ML", "ml"

    restaurant = models.ForeignKey(
        "accounts.Restaurant",
        on_delete=models.PROTECT,
        related_name="inventory_items",
    )
    name = models.CharField(max_length=180)
    sku = models.CharField(max_length=60)  # unique per restaurant
    unit = models.CharField(max_length=5, choices=Unit.choices, default=Unit.PCS)

    current_stock = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    reorder_level = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    cost_per_unit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["restaurant", "sku"],
                name="uq_inventoryitem_restaurant_sku",
            ),
        ]
        indexes = [
            models.Index(fields=["restaurant", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"


class StockMovement(models.Model):
    class Type(models.TextChoices):
        IN_ = "IN", "Stock In"
        OUT = "OUT", "Stock Out"
        ADJUST = "ADJUST", "Adjust (+/-)"

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="movements")
    movement_type = models.CharField(max_length=10, choices=Type.choices)

    # For IN/OUT: quantity should be positive
    # For ADJUST: quantity can be + or - (delta)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)

    reason = models.CharField(max_length=120, blank=True)  # e.g., Purchase, Waste, Manual
    note = models.TextField(blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stock_movements"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.movement_type} {self.quantity} {self.item.sku}"
