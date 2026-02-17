from decimal import Decimal
from django.db import transaction
from rest_framework import serializers

from .models import InventoryItem, StockMovement


class InventoryItemSerializer(serializers.ModelSerializer):
    restaurant = serializers.IntegerField(source="restaurant_id", read_only=True)

    class Meta:
        model = InventoryItem
        fields = (
            "id",
            "restaurant",
            "name",
            "sku",
            "unit",
            "current_stock",
            "reorder_level",
            "cost_per_unit",
            "is_active",
            "created_at",
            "updated_at",
        )


class StockMovementSerializer(serializers.ModelSerializer):
    item = serializers.IntegerField(source="item_id", read_only=True)
    item_name = serializers.CharField(source="item.name", read_only=True)
    item_sku = serializers.CharField(source="item.sku", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = StockMovement
        fields = (
            "id",
            "created_at",
            "item",
            "item_name",
            "item_sku",
            "movement_type",
            "quantity",
            "reason",
            "note",
            "created_by_email",
        )


class StockMovementCreateSerializer(serializers.Serializer):
    item = serializers.IntegerField()
    movement_type = serializers.ChoiceField(choices=StockMovement.Type.choices)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2)
    reason = serializers.CharField(required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True)

    @transaction.atomic
    def create(self, validated_data):
        user = self.context["request"].user
        restaurant_id = getattr(user, "restaurant_id", None)
        if not restaurant_id and not user.is_superuser:
            raise serializers.ValidationError({"detail": "User has no restaurant assigned."})

        item_id = validated_data["item"]
        movement_type = validated_data["movement_type"]
        qty: Decimal = validated_data["quantity"]

        item_qs = InventoryItem.objects.select_for_update().filter(pk=item_id)
        if not user.is_superuser:
            item_qs = item_qs.filter(restaurant_id=restaurant_id)

        item = item_qs.first()
        if not item:
            raise serializers.ValidationError({"item": "Inventory item not found in your restaurant."})

        if movement_type in ["IN", "OUT"] and qty <= 0:
            raise serializers.ValidationError({"quantity": "Quantity must be > 0 for IN/OUT."})

        if movement_type == "IN":
            delta = qty
        elif movement_type == "OUT":
            delta = -qty
        else:
            delta = qty  # ADJUST (+/-)

        new_stock = (item.current_stock + delta).quantize(Decimal("0.01"))
        if new_stock < 0:
            raise serializers.ValidationError({"quantity": "Not enough stock to remove."})

        item.current_stock = new_stock
        item.save(update_fields=["current_stock", "updated_at"])

        movement = StockMovement.objects.create(
            item=item,
            movement_type=movement_type,
            quantity=qty,
            reason=validated_data.get("reason", ""),
            note=validated_data.get("note", ""),
            created_by=user,
        )
        return movement
