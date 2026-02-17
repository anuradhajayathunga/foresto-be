from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from inventory.models import InventoryItem, StockMovement
from menu.models import MenuItem, RecipeLine
from .models import Sale, SaleItem


class SaleItemCreateSerializer(serializers.Serializer):
    menu_item = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False, allow_blank=True)
    qty = serializers.IntegerField(min_value=1)


class SaleItemSerializer(serializers.ModelSerializer):
    menu_item = serializers.IntegerField(source="menu_item_id", read_only=True)
    menu_item_name = serializers.CharField(source="menu_item.name", read_only=True)

    class Meta:
        model = SaleItem
        fields = ("id", "menu_item", "menu_item_name", "name", "qty", "unit_price", "line_total")


class SaleSerializer(serializers.ModelSerializer):
    restaurant = serializers.IntegerField(source="restaurant_id", read_only=True)
    items = SaleItemSerializer(many=True, read_only=True)

    class Meta:
        model = Sale
        fields = (
            "id",
            "restaurant",
            "created_at",
            "created_by",
            "customer_name",
            "status",
            "payment_method",
            "subtotal",
            "discount",
            "tax",
            "total",
            "notes",
            "items",
        )
        read_only_fields = ("created_by", "subtotal", "total", "restaurant")


class SaleCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(required=False, allow_blank=True)
    payment_method = serializers.ChoiceField(choices=Sale.PaymentMethod.choices)
    status = serializers.ChoiceField(choices=Sale.Status.choices)
    discount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"))
    tax = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"))
    notes = serializers.CharField(required=False, allow_blank=True)
    items = SaleItemCreateSerializer(many=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("At least one item is required.")
        return items

    @transaction.atomic
    def create(self, validated):
        user = self.context["request"].user
        restaurant = getattr(user, "restaurant", None)
        if not restaurant and not user.is_superuser:
            raise serializers.ValidationError({"detail": "User has no restaurant assigned."})

        discount = validated.get("discount", Decimal("0.00"))
        tax = validated.get("tax", Decimal("0.00"))

        sale = Sale.objects.create(
            restaurant=restaurant,
            created_by=user,
            customer_name=validated.get("customer_name", ""),
            payment_method=validated["payment_method"],
            status=validated["status"],
            discount=discount,
            tax=tax,
            notes=validated.get("notes", ""),
        )

        subtotal = Decimal("0.00")

        for idx, it in enumerate(validated["items"]):
            qty = int(it["qty"])
            menu_item_id = it.get("menu_item")

            if menu_item_id:
                mi_qs = MenuItem.objects.filter(id=menu_item_id)
                if not user.is_superuser:
                    mi_qs = mi_qs.filter(restaurant_id=user.restaurant_id)
                mi = mi_qs.first()
                if not mi:
                    raise serializers.ValidationError({"items": f"Menu item {menu_item_id} not found in your restaurant."})

                name = mi.name
                unit_price = mi.price
                menu_item = mi
            else:
                name = (it.get("name") or "").strip()
                if not name:
                    raise serializers.ValidationError({"items": "Item name required when menu_item not provided."})
                unit_price = Decimal("0.00")
                menu_item = None

            line_total = (Decimal(qty) * Decimal(unit_price)).quantize(Decimal("0.01"))
            subtotal += line_total

            SaleItem.objects.create(
                sale=sale,
                menu_item=menu_item,
                name=name,
                qty=qty,
                unit_price=unit_price,
                line_total=line_total,
                sort_order=idx,
            )

        total = (subtotal - discount + tax).quantize(Decimal("0.01"))
        if total < 0:
            total = Decimal("0.00")

        sale.subtotal = subtotal.quantize(Decimal("0.01"))
        sale.total = total
        sale.save(update_fields=["subtotal", "total"])

        if sale.status == Sale.Status.PAID:
            deduct_inventory_for_sale(sale)

        return sale


def deduct_inventory_for_sale(sale: Sale):
    """
    Deduct ingredients based on recipes for sale items.
    Creates StockMovement OUT entries.
    """
    if sale.inventory_deducted:
        return

    if not getattr(sale, "restaurant_id", None):
        raise serializers.ValidationError({"detail": "Sale has no restaurant assigned."})

    required = defaultdict(Decimal)  # ingredient_id -> total_qty_needed
    sale_items = sale.items.select_related("menu_item").all()

    menu_item_ids = [si.menu_item_id for si in sale_items if si.menu_item_id]
    if not menu_item_ids:
        sale.inventory_deducted = True
        sale.save(update_fields=["inventory_deducted"])
        return

    recipe_lines = RecipeLine.objects.filter(
        menu_item_id__in=menu_item_ids,
        menu_item__restaurant_id=sale.restaurant_id,
        ingredient__restaurant_id=sale.restaurant_id,
    ).select_related("ingredient")

    recipe_by_menu = defaultdict(list)
    for rl in recipe_lines:
        recipe_by_menu[rl.menu_item_id].append(rl)

    for si in sale_items:
        if not si.menu_item_id:
            continue
        for rl in recipe_by_menu.get(si.menu_item_id, []):
            required[rl.ingredient_id] += (rl.qty * Decimal(si.qty)).quantize(Decimal("0.01"))

    if not required:
        sale.inventory_deducted = True
        sale.save(update_fields=["inventory_deducted"])
        return

    inv_ids = list(required.keys())
    items = InventoryItem.objects.select_for_update().filter(
        id__in=inv_ids,
        restaurant_id=sale.restaurant_id,
    )
    item_map = {it.id: it for it in items}

    for ing_id, need in required.items():
        it = item_map.get(ing_id)
        if not it:
            raise serializers.ValidationError({"detail": f"Ingredient {ing_id} not found in this restaurant."})
        if it.current_stock < need:
            raise serializers.ValidationError({
                "detail": (
                    f"Not enough stock for {it.name} ({it.sku}). "
                    f"Have {it.current_stock}, need {need}."
                )
            })

    for ing_id, need in required.items():
        it = item_map[ing_id]
        it.current_stock = (it.current_stock - need).quantize(Decimal("0.01"))
        it.save(update_fields=["current_stock", "updated_at"])

        StockMovement.objects.create(
            item=it,
            movement_type="OUT",
            quantity=need,
            reason="Sale",
            note=f"Auto-deduct for Sale #{sale.id}",
            created_by=sale.created_by,
        )

    sale.inventory_deducted = True
    sale.save(update_fields=["inventory_deducted"])
