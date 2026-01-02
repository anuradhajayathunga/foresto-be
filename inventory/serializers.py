from rest_framework import serializers
from .models import (
    Store, Supplier, Ingredient, MenuItem,
    InventoryRecord, RecipeComponent,
    PurchaseOrder, PurchaseOrderItem
)


class StoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Store
        fields = ["id", "name", "address", "phone", "owner_id"]
        read_only_fields = ["owner_id"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "contact_person", "phone", "whatsapp_number", "email", "address"]


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = [
            "id",
            "sku",
            "name",
            "unit_of_measure",
            "description",
            "min_stock_level",
            "target_stock_level",
            "default_supplier",
        ]


class MenuItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = ["id", "code", "name", "category", "unit", "description", "is_active"]


class InventoryRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryRecord
        fields = ["id", "store", "ingredient", "quantity_on_hand", "last_updated_at"]
        read_only_fields = ["last_updated_at"]


class RecipeComponentSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer(read_only=True)
    ingredient_id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source="ingredient",
        write_only=True,
    )

    class Meta:
        model = RecipeComponent
        fields = [
            "id",
            "menu_item",
            "ingredient",
            "ingredient_id",
            "quantity_per_portion",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["menu_item", "created_at", "updated_at"]


# =============================
# SMART PO SERIALIZERS (STEP 7)
# =============================

class PurchaseOrderItemSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(
        source="ingredient.name", read_only=True
    )

    class Meta:
        model = PurchaseOrderItem
        fields = ["ingredient", "ingredient_name", "ordered_quantity"]


class PurchaseOrderSerializer(serializers.ModelSerializer):
    items = PurchaseOrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "store",
            "supplier",
            "status",
            "created_at",
            "expected_delivery_date",
            "items",
        ]
