from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SupplierViewSet, PurchaseInvoiceViewSet

router = DefaultRouter()
router.register("suppliers", SupplierViewSet, basename="suppliers")
router.register("invoices", PurchaseInvoiceViewSet, basename="purchase-invoices")

urlpatterns = [path("", include(router.urls))]
