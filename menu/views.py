from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from accounts.tenancy import READ_ROLES, WRITE_ROLES, assert_restaurant_access
from .models import Category, MenuItem, RecipeLine
from .serializers import CategorySerializer, MenuItemSerializer, RecipeLineSerializer


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_active"]
    search_fields = ["name", "slug"]
    ordering_fields = ["sort_order", "name"]

    def get_queryset(self):
        restaurant_id, _ = assert_restaurant_access(self.request, allowed_roles=READ_ROLES)
        return Category.objects.filter(restaurant_id=restaurant_id)

    def perform_create(self, serializer):
        restaurant_id, _ = assert_restaurant_access(self.request, allowed_roles=WRITE_ROLES)
        serializer.save(restaurant_id=restaurant_id)

    def perform_update(self, serializer):
        assert_restaurant_access(self.request, allowed_roles=WRITE_ROLES)
        serializer.save()

    def perform_destroy(self, instance):
        assert_restaurant_access(self.request, allowed_roles=WRITE_ROLES)
        instance.delete()


class MenuItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_fields = ["category", "is_available"]
    search_fields = ["name", "description", "category__name"]
    ordering_fields = ["sort_order", "name", "price", "created_at"]

    def get_queryset(self):
        restaurant_id, _ = assert_restaurant_access(self.request, allowed_roles=READ_ROLES)
        return MenuItem.objects.select_related("category").filter(
            category__restaurant_id=restaurant_id
        )

    def get_serializer_class(self):
        return MenuItemSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        restaurant_id, _ = assert_restaurant_access(self.request, allowed_roles=READ_ROLES)
        ctx["restaurant_id"] = restaurant_id
        return ctx

    def perform_create(self, serializer):
        assert_restaurant_access(self.request, allowed_roles=WRITE_ROLES)
        serializer.save()

    def perform_update(self, serializer):
        assert_restaurant_access(self.request, allowed_roles=WRITE_ROLES)
        serializer.save()

    def perform_destroy(self, instance):
        assert_restaurant_access(self.request, allowed_roles=WRITE_ROLES)
        instance.delete()


class RecipeLineViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filterset_fields = ["menu_item", "ingredient"]

    def get_queryset(self):
        restaurant_id, _ = assert_restaurant_access(self.request, allowed_roles=READ_ROLES)
        return RecipeLine.objects.select_related("menu_item", "ingredient").filter(
            menu_item__category__restaurant_id=restaurant_id,
            ingredient__restaurant_id=restaurant_id,
        )

    def get_serializer_class(self):
        return RecipeLineSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        restaurant_id, _ = assert_restaurant_access(self.request, allowed_roles=READ_ROLES)
        ctx["restaurant_id"] = restaurant_id
        return ctx

    def perform_create(self, serializer):
        assert_restaurant_access(self.request, allowed_roles=WRITE_ROLES)
        serializer.save()

    def perform_update(self, serializer):
        assert_restaurant_access(self.request, allowed_roles=WRITE_ROLES)
        serializer.save()

    def perform_destroy(self, instance):
        assert_restaurant_access(self.request, allowed_roles=WRITE_ROLES)
        instance.delete()
