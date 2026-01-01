from rest_framework import viewsets
from .models import Category, MenuItem, RecipeLine
from .serializers import CategorySerializer, MenuItemSerializer, RecipeLineSerializer
from .permissions import IsStaffOrReadOnly
from rest_framework import viewsets
from inventory.permissions import IsStaff  # reuse staff permission

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ["is_active"]
    search_fields = ["name", "slug"]
    ordering_fields = ["sort_order", "name"]

class MenuItemViewSet(viewsets.ModelViewSet):
    queryset = MenuItem.objects.select_related("category").all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsStaffOrReadOnly]
    filterset_fields = ["category", "is_available"]
    search_fields = ["name", "description", "category__name"]
    ordering_fields = ["sort_order", "name", "price", "created_at"]

class RecipeLineViewSet(viewsets.ModelViewSet):
    queryset = RecipeLine.objects.select_related("menu_item", "ingredient").all()
    serializer_class = RecipeLineSerializer
    permission_classes = [IsStaff]
    filterset_fields = ["menu_item", "ingredient"]
