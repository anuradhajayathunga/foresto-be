from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.db.models import F

from .models import InventoryItem, StockMovement
from .serializers import (
    InventoryItemSerializer,
    StockMovementSerializer,
    StockMovementCreateSerializer,
)
from .permissions import IsStaff

class InventoryItemViewSet(viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsStaff]
    filterset_fields = ["is_active", "unit"]
    search_fields = ["name", "sku"]
    ordering_fields = ["name", "current_stock", "reorder_level", "updated_at"]

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        qs = self.get_queryset().filter(is_active=True, current_stock__lte=F("reorder_level")).order_by("name")
        data = InventoryItemSerializer(qs, many=True).data
        return Response(data)


    

class StockMovementViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = StockMovement.objects.select_related("item", "created_by").all()
    permission_classes = [IsStaff]
    filterset_fields = ["movement_type", "item"]
    search_fields = ["item__name", "item__sku", "reason", "note"]
    ordering_fields = ["created_at", "quantity"]

    def get_serializer_class(self):
        if self.action == "create":
            return StockMovementCreateSerializer
        return StockMovementSerializer

    # ✅ critical fix: use output serializer for response
    def create(self, request, *args, **kwargs):
        serializer = StockMovementCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        movement = serializer.save()

        out = StockMovementSerializer(movement, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

