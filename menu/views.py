from rest_framework import viewsets

from core.mixins import RestaurantScopedQuerysetMixin
from inventory.permissions import IsStaff
from .models import Category, MenuItem, RecipeLine
from .permissions import IsStaffOrReadOnly
from .serializers import CategorySerializer, MenuItemSerializer, RecipeLineSerializer


class CategoryViewSet(RestaurantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ["is_active"]
    search_fields = ["name", "slug"]
    ordering_fields = ["sort_order", "name"]


class MenuItemViewSet(RestaurantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = MenuItem.objects.select_related("category").all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ["category", "is_available"]
    search_fields = ["name", "description", "category__name"]
    ordering_fields = ["sort_order", "name", "price", "created_at"]


class RecipeLineViewSet(RestaurantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = RecipeLine.objects.select_related("menu_item", "ingredient").all()
    serializer_class = RecipeLineSerializer
    permission_classes = [IsStaff]
    filterset_fields = ["menu_item", "ingredient"]
    restaurant_lookup = "menu_item__restaurant"
