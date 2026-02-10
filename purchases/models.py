from decimal import Decimal
from django.conf import settings
from django.db import models

class Supplier(models.Model):
    name = models.CharField(max_length=180)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class PurchaseInvoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"        
        POSTED = "POSTED", "Posted"
        VOID = "VOID", "Void"

    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="invoices")
    invoice_no = models.CharField(max_length=80, blank=True)  # optional supplier invoice number
    invoice_date = models.DateField()

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.POSTED)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    note = models.TextField(blank=True)

    voided_at = models.DateTimeField(null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="voided_purchase_invoices",
    )
    void_reason = models.CharField(max_length=200, blank=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="purchase_invoices")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-invoice_date", "-id"]

    def __str__(self):
        return f"Purchase #{self.id} - {self.supplier.name}"


class PurchaseLine(models.Model):
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.CASCADE, related_name="lines")
    item = models.ForeignKey("inventory.InventoryItem", on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.item.name} x {self.qty}"
