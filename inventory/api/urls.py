from django.urls import path, include
from rest_framework.routers import DefaultRouter
from inventory.api.views import (
    StoreViewSet,
    InventoryViewSet,
    PurchaseOrderViewSet,
)
from inventory.api.auto_po import AutoPOView

router = DefaultRouter()
router.register("stores", StoreViewSet)
router.register("inventory", InventoryViewSet)
router.register("purchase-orders", PurchaseOrderViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("auto-po/", AutoPOView.as_view(), name="auto-po"),
]
