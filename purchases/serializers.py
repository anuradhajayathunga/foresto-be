from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from inventory.models import InventoryItem, StockMovement
from .models import PurchaseInvoice, PurchaseLine, Supplier


class SupplierSerializer(serializers.ModelSerializer):
    restaurant = serializers.IntegerField(source="restaurant_id", read_only=True)

    class Meta:
        model = Supplier
        fields = ("id", "restaurant", "name", "email", "phone", "address", "is_active")
        read_only_fields = ("restaurant",)


class PurchaseLineOutSerializer(serializers.ModelSerializer):
    item = serializers.IntegerField(source="item_id", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_sku = serializers.CharField(source="item.sku", read_only=True)

    class Meta:
        model = PurchaseLine
        fields = ("id", "item", "item_name", "item_sku", "qty", "unit_cost", "line_total")


class PurchaseInvoiceOutSerializer(serializers.ModelSerializer):
    restaurant = serializers.IntegerField(source="restaurant_id", read_only=True)
    supplier = serializers.IntegerField(source="supplier_id", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    lines = PurchaseLineOutSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseInvoice
        fields = (
            "id",
            "restaurant",
            "supplier",
            "supplier_name",
            "invoice_no",
            "invoice_date",
            "status",
            "subtotal",
            "discount",
            "tax",
            "total",
            "note",
            "created_by",
            "created_at",
            "lines",
        )


class PurchaseLineInSerializer(serializers.Serializer):
    item = serializers.IntegerField()
    qty = serializers.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = serializers.DecimalField(max_digits=12, decimal_places=2)


class PurchaseInvoiceCreateSerializer(serializers.Serializer):
    supplier = serializers.IntegerField()
    invoice_no = serializers.CharField(required=False, allow_blank=True)
    invoice_date = serializers.DateField()
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"))
    tax = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"))
    note = serializers.CharField(required=False, allow_blank=True)
    lines = PurchaseLineInSerializer(many=True)

    def validate_lines(self, lines):
        if not lines:
            raise serializers.ValidationError("At least one line is required.")
        for l in lines:
            if l["qty"] <= 0:
                raise serializers.ValidationError("Qty must be > 0.")
            if l["unit_cost"] < 0:
                raise serializers.ValidationError("Unit cost cannot be negative.")
        return lines

    @transaction.atomic
    def create(self, validated):
        user = self.context["request"].user
        restaurant = getattr(user, "restaurant", None)
        if not restaurant and not user.is_superuser:
            raise serializers.ValidationError({"detail": "User has no restaurant assigned."})

        supplier_id = validated["supplier"]
        supplier_qs = Supplier.objects.filter(pk=supplier_id)
        if not user.is_superuser:
            supplier_qs = supplier_qs.filter(restaurant_id=user.restaurant_id)
        supplier = supplier_qs.first()
        if not supplier:
            raise serializers.ValidationError({"supplier": "Supplier not found in your restaurant."})

        discount = validated.get("discount", Decimal("0.00"))
        tax = validated.get("tax", Decimal("0.00"))

        invoice = PurchaseInvoice.objects.create(
            restaurant=restaurant,
            supplier=supplier,
            invoice_no=validated.get("invoice_no", ""),
            invoice_date=validated["invoice_date"],
            discount=discount,
            tax=tax,
            note=validated.get("note", ""),
            created_by=user,
            status=PurchaseInvoice.Status.POSTED,
        )

        subtotal = Decimal("0.00")

        for idx, l in enumerate(validated["lines"]):
            item_qs = InventoryItem.objects.select_for_update().filter(pk=l["item"])
            if not user.is_superuser:
                item_qs = item_qs.filter(restaurant_id=user.restaurant_id)
            item = item_qs.first()
            if not item:
                raise serializers.ValidationError({"lines": f"Inventory item {l['item']} not found in your restaurant."})

            qty = Decimal(l["qty"]).quantize(Decimal("0.01"))
            unit_cost = Decimal(l["unit_cost"]).quantize(Decimal("0.01"))
            line_total = (qty * unit_cost).quantize(Decimal("0.01"))
            subtotal += line_total

            PurchaseLine.objects.create(
                invoice=invoice,
                item=item,
                qty=qty,
                unit_cost=unit_cost,
                line_total=line_total,
                sort_order=idx,
            )

            item.current_stock = (item.current_stock + qty).quantize(Decimal("0.01"))
            item.cost_per_unit = unit_cost
            item.save(update_fields=["current_stock", "cost_per_unit", "updated_at"])

            StockMovement.objects.create(
                item=item,
                movement_type=StockMovement.Type.IN_,
                quantity=qty,
                reason="Purchase",
                note=f"PurchaseInvoice #{invoice.id}",
                created_by=user,
            )

        total = (subtotal - discount + tax).quantize(Decimal("0.01"))
        if total < 0:
            total = Decimal("0.00")

        invoice.subtotal = subtotal.quantize(Decimal("0.01"))
        invoice.total = total
        invoice.save(update_fields=["subtotal", "total"])

        return invoice


class PurchaseVoidSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, max_length=200)


class PurchaseDraftFromForecastSerializer(serializers.Serializer):
    supplier = serializers.IntegerField()
    scope = serializers.ChoiceField(choices=["tomorrow", "next7"], default="next7")
    horizon_days = serializers.IntegerField(required=False, default=7)
    top_n = serializers.IntegerField(required=False, default=50)
    include_ok = serializers.BooleanField(required=False, default=False)
    invoice_date = serializers.DateField(required=False)
    note = serializers.CharField(required=False, allow_blank=True)
