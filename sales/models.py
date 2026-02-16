from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone

class Sale(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "CASH", "Cash"
        CARD = "CARD", "Card"
        ONLINE = "ONLINE", "Online"

    class Status(models.TextChoices):
        PAID = "PAID", "Paid"
        VOID = "VOID", "Void"
        DRAF = "DRAF", "Draf"

    restaurant = models.ForeignKey(
        "accounts.Restaurant",
        on_delete=models.CASCADE,
        related_name="sale",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="sales"
    )

    customer_name = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAF)
    payment_method = models.CharField(max_length=10, choices=PaymentMethod.choices, default=PaymentMethod.CASH)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    notes = models.TextField(blank=True)

    inventory_deducted = models.BooleanField(default=False)
    
    sold_at = models.DateTimeField(default=timezone.now, db_index=True)
    import_ref = models.CharField(max_length=120, unique=True, null=True, blank=True)


    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["restaurant", "created_at"])]
    def __str__(self):
        return f"Sale #{self.id} - {self.total}"


class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name="items")
    restaurant = models.ForeignKey(
        "accounts.Restaurant",
        on_delete=models.CASCADE,
        related_name="sale_item",
        null=True,
        blank=True,
    )
    # optional link to menu item (keep snapshot fields too)
    menu_item = models.ForeignKey("menu.MenuItem", on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=180)  # snapshot
    qty = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        indexes = [models.Index(fields=["restaurant", "sale", "menu_item"])]
    def __str__(self):
        return f"{self.name} x{self.qty}"
