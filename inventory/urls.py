from django.urls import path
from .views import (
    StoreListCreateView,
    SupplierListCreateView,
    IngredientListCreateView,
    MenuItemListCreateView,
    InventoryRecordListCreateView,
    RecipeComponentListCreateView,   # 👈
    RecipeComponentDestroyView,      # 👈
       
)

urlpatterns = [
    path("stores/", StoreListCreateView.as_view(), name="store-list-create"),
    path("suppliers/", SupplierListCreateView.as_view(), name="supplier-list-create"),
    path("ingredients/", IngredientListCreateView.as_view(), name="ingredient-list-create"),
    path("menu-items/", MenuItemListCreateView.as_view(), name="menuitem-list-create"),
    path("inventory/", InventoryRecordListCreateView.as_view(), name="inventory-list-create"),
      path(
        "menu-items/<int:menu_item_id>/recipe/",
        RecipeComponentListCreateView.as_view(),
        name="recipecomponent-list-create",
    ),
    path(
        "recipe-components/<int:pk>/",
        RecipeComponentDestroyView.as_view(),
        name="recipecomponent-destroy",
    ),
]
