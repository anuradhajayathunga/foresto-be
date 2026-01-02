from rest_framework.viewsets import ReadOnlyModelViewSet
from inventory.models import Store, InventoryRecord, PurchaseOrder
from inventory.serializers import (
    StoreSerializer,
    InventoryRecordSerializer,
    PurchaseOrderSerializer,
)


class StoreViewSet(ReadOnlyModelViewSet):
    queryset = Store.objects.all()
    serializer_class = StoreSerializer


class InventoryViewSet(ReadOnlyModelViewSet):
    queryset = InventoryRecord.objects.select_related("ingredient", "store")
    serializer_class = InventoryRecordSerializer


class PurchaseOrderViewSet(ReadOnlyModelViewSet):
    queryset = PurchaseOrder.objects.prefetch_related("items")
    serializer_class = PurchaseOrderSerializer
