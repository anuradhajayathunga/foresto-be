from rest_framework import serializers
from .models import Category, MenuItem, RecipeLine
from django.utils.text import slugify
from rest_framework import serializers
from .models import RecipeLine
from inventory.models import InventoryItem
from menu.models import MenuItem

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "sort_order", "is_active")

    def validate(self, attrs):
        # auto slug if missing
        name = attrs.get("name") or getattr(self.instance, "name", "")
        slug = attrs.get("slug") or slugify(name)
        attrs["slug"] = slug
        return attrs

class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = MenuItem
        fields = (
            "id",
            "category",
            "category_name",
            "name",
            "slug",
            "description",
            "price",
            "is_available",
            "sort_order",
            "created_at",
        )

    def validate(self, attrs):
        # auto slug if missing
        name = attrs.get("name") or getattr(self.instance, "name", "")
        slug = attrs.get("slug") or slugify(name)
        attrs["slug"] = slug
        return attrs

class RecipeLineSerializer(serializers.ModelSerializer):
    menu_item = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.all())
    ingredient = serializers.PrimaryKeyRelatedField(queryset=InventoryItem.objects.all())

    ingredient_name = serializers.CharField(source="ingredient.name", read_only=True)
    ingredient_unit = serializers.CharField(source="ingredient.unit", read_only=True)
    ingredient_sku = serializers.CharField(source="ingredient.sku", read_only=True)

    class Meta:
        model = RecipeLine
        fields = (
            "id",
            "menu_item",
            "ingredient",
            "ingredient_name",
            "ingredient_unit",
            "ingredient_sku",
            "qty",
        )

