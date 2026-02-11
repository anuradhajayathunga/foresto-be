from django.utils.text import slugify
from rest_framework import serializers

from inventory.models import InventoryItem
from .models import Category, MenuItem, RecipeLine


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "sort_order", "is_active")

    def validate(self, attrs):
        name = attrs.get("name") or getattr(self.instance, "name", "")
        slug = attrs.get("slug") or slugify(name)
        attrs["slug"] = slug
        return attrs


class MenuItemSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.none())
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        restaurant_id = self.context.get("restaurant_id")
        if restaurant_id:
            self.fields["category"].queryset = Category.objects.filter(
                restaurant_id=restaurant_id
            )

    def validate(self, attrs):
        name = attrs.get("name") or getattr(self.instance, "name", "")
        slug = attrs.get("slug") or slugify(name)
        attrs["slug"] = slug

        category = attrs.get("category") or getattr(self.instance, "category", None)
        restaurant_id = self.context.get("restaurant_id")
        if category and restaurant_id and category.restaurant_id != restaurant_id:
            raise serializers.ValidationError({"category": "Category is outside current restaurant."})
        return attrs


class RecipeLineSerializer(serializers.ModelSerializer):
    menu_item = serializers.PrimaryKeyRelatedField(queryset=MenuItem.objects.none())
    ingredient = serializers.PrimaryKeyRelatedField(queryset=InventoryItem.objects.none())

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        restaurant_id = self.context.get("restaurant_id")
        if restaurant_id:
            self.fields["menu_item"].queryset = MenuItem.objects.filter(
                category__restaurant_id=restaurant_id
            )
            self.fields["ingredient"].queryset = InventoryItem.objects.filter(
                restaurant_id=restaurant_id
            )

    def validate(self, attrs):
        menu_item = attrs.get("menu_item") or getattr(self.instance, "menu_item", None)
        ingredient = attrs.get("ingredient") or getattr(self.instance, "ingredient", None)
        restaurant_id = self.context.get("restaurant_id")

        if restaurant_id and menu_item and menu_item.category.restaurant_id != restaurant_id:
            raise serializers.ValidationError({"menu_item": "Menu item is outside current restaurant."})

        if restaurant_id and ingredient and ingredient.restaurant_id != restaurant_id:
            raise serializers.ValidationError({"ingredient": "Ingredient is outside current restaurant."})

        if menu_item and ingredient and menu_item.category.restaurant_id != ingredient.restaurant_id:
            raise serializers.ValidationError("Recipe lines must link menu item and ingredient in same restaurant.")

        return attrs
