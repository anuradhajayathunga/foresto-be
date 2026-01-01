from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import InventoryItemViewSet, StockMovementViewSet

router = DefaultRouter()
router.register("items", InventoryItemViewSet, basename="inventory-items")
router.register("movements", StockMovementViewSet, basename="stock-movements")

urlpatterns = [
    path("", include(router.urls)),
]
