from rest_framework import generics, permissions
from .models import Store, Supplier, Ingredient, MenuItem, InventoryRecord, RecipeComponent
from .serializers import (
    StoreSerializer,
    SupplierSerializer,
    IngredientSerializer,
    MenuItemSerializer,
    InventoryRecordSerializer,
    RecipeComponent,
    RecipeComponentSerializer, 
)


class StoreListCreateView(generics.ListCreateAPIView):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None 

    def perform_create(self, serializer):
        serializer.save(owner_id=self.request.user)


class SupplierListCreateView(generics.ListCreateAPIView):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [permissions.IsAuthenticated]


class IngredientListCreateView(generics.ListCreateAPIView):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [permissions.IsAuthenticated]

class MenuItemListCreateView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticated]
class MenuItemRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/inventory/menu-items/<id>/
    PUT    /api/inventory/menu-items/<id>/
    PATCH  /api/inventory/menu-items/<id>/
    DELETE /api/inventory/menu-items/<id>/
    """
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [permissions.IsAuthenticated]

class InventoryRecordListCreateView(generics.ListCreateAPIView):
    queryset = InventoryRecord.objects.all()
    serializer_class = InventoryRecordSerializer
    permission_classes = [permissions.IsAuthenticated]

class RecipeComponentListCreateView(generics.ListCreateAPIView):
    """
    GET /api/inventory/menu-items/<menu_item_id>/recipe/
    POST /api/inventory/menu-items/<menu_item_id>/recipe/
    """
    serializer_class = RecipeComponentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        menu_item_id = self.kwargs["menu_item_id"]
        return (
            RecipeComponent.objects
            .filter(menu_item_id=menu_item_id)
            .select_related("ingredient", "menu_item")
        )

    def perform_create(self, serializer):
        menu_item_id = self.kwargs["menu_item_id"]
        menu_item = MenuItem.objects.get(pk=menu_item_id)
        serializer.save(menu_item=menu_item)


class RecipeComponentDestroyView(generics.DestroyAPIView):
    """
    DELETE /api/inventory/recipe-components/<pk>/
    """
    queryset = RecipeComponent.objects.all()
    serializer_class = RecipeComponentSerializer
    permission_classes = [permissions.IsAuthenticated]