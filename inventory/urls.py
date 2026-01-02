from django.urls import path
from .views import (
    StoreListCreateView, SupplierListCreateView,
    IngredientListCreateView, MenuItemListCreateView,
    InventoryRecordListCreateView, RecipeComponentListCreateView,
    RecipeComponentDestroyView
)
from .views_supplier import (
    SupplierDashboardView, SupplierForecastView,
    SupplierPurchaseSuggestionsView, SupplierPerformanceView,
    supplier_low_stock_alerts
)

urlpatterns = [
    # Existing routes
    path('stores/', StoreListCreateView.as_view(), name='store-list'),
    path('suppliers/', SupplierListCreateView.as_view(), name='supplier-list'),
    path('ingredients/', IngredientListCreateView.as_view(), name='ingredient-list'),
    path('menu-items/', MenuItemListCreateView.as_view(), name='menuitem-list'),
    path('inventory/', InventoryRecordListCreateView.as_view(), name='inventory-list'),
    path('menu-items/<int:menu_item_id>/recipe/', RecipeComponentListCreateView.as_view(), name='recipe-list'),
    path('recipe-components/<int:pk>/', RecipeComponentDestroyView.as_view(), name='recipe-detail'),
    
    # New supplier dashboard routes
    path('suppliers/<int:supplier_id>/dashboard/', SupplierDashboardView.as_view(), name='supplier-dashboard'),
    path('suppliers/<int:supplier_id>/forecast/', SupplierForecastView.as_view(), name='supplier-forecast'),
    path('suppliers/<int:supplier_id>/suggest-purchase/', SupplierPurchaseSuggestionsView.as_view(), name='supplier-purchase-suggestions'),
    path('suppliers/<int:supplier_id>/performance/', SupplierPerformanceView.as_view(), name='supplier-performance'),
    path('suppliers/<int:supplier_id>/low-stock-alerts/', supplier_low_stock_alerts, name='supplier-low-stock-alerts'),
]