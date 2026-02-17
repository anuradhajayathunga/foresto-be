from django.utils.text import slugify
from rest_framework import serializers

from inventory.models import InventoryItem
from .models import Category, MenuItem, RecipeLine


class CategorySerializer(serializers.ModelSerializer):
    restaurant = serializers.IntegerField(source="restaurant_id", read_only=True)

    class Meta:
        model = Category
        fields = ("id", "restaurant", "name", "slug", "sort_order", "is_active")

    def validate(self, attrs):
        name = (attrs.get("name") or getattr(self.instance, "name", "")).strip()
        slug = (attrs.get("slug") or slugify(name)).strip()
        attrs["slug"] = slug

        req = self.context.get("request")
        user = getattr(req, "user", None)
        restaurant_id = getattr(user, "restaurant_id", None)

        # Tenant-scoped uniqueness safety (before DB constraint catches it)
        if restaurant_id:
            qs = Category.objects.filter(restaurant_id=restaurant_id)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if name and qs.filter(name__iexact=name).exists():
                raise serializers.ValidationError({"name": "Category name already exists in your restaurant."})
            if slug and qs.filter(slug=slug).exists():
                raise serializers.ValidationError({"slug": "Category slug already exists in your restaurant."})

        return attrs


class MenuItemSerializer(serializers.ModelSerializer):
    restaurant = serializers.IntegerField(source="restaurant_id", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = MenuItem
        fields = (
            "id",
            "restaurant",
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
        read_only_fields = ("restaurant",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        req = self.context.get("request")
        user = getattr(req, "user", None)

        if user and user.is_authenticated and not user.is_superuser and getattr(user, "restaurant_id", None):
            self.fields["category"].queryset = Category.objects.filter(restaurant_id=user.restaurant_id)

    def validate(self, attrs):
        name = (attrs.get("name") or getattr(self.instance, "name", "")).strip()
        slug = (attrs.get("slug") or slugify(name)).strip()
        attrs["slug"] = slug

        req = self.context.get("request")
        user = getattr(req, "user", None)
        category = attrs.get("category") or getattr(self.instance, "category", None)

        if user and user.is_authenticated and not user.is_superuser and getattr(user, "restaurant_id", None):
            if category and category.restaurant_id != user.restaurant_id:
                raise serializers.ValidationError({"category": "Category does not belong to your restaurant."})

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        req = self.context.get("request")
        user = getattr(req, "user", None)

        if user and user.is_authenticated and not user.is_superuser and getattr(user, "restaurant_id", None):
            rid = user.restaurant_id
            self.fields["menu_item"].queryset = MenuItem.objects.filter(restaurant_id=rid)
            self.fields["ingredient"].queryset = InventoryItem.objects.filter(restaurant_id=rid)

    def validate(self, attrs):
        menu_item = attrs.get("menu_item") or getattr(self.instance, "menu_item", None)
        ingredient = attrs.get("ingredient") or getattr(self.instance, "ingredient", None)

        if menu_item and ingredient and menu_item.restaurant_id != ingredient.restaurant_id:
            raise serializers.ValidationError("Menu item and ingredient must belong to the same restaurant.")

        return attrs
