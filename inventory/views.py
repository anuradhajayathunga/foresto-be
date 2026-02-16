from django.db.models import F
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import RestaurantScopedQuerysetMixin
from .models import InventoryItem, StockMovement
from .permissions import IsStaff
from .serializers import (
    InventoryItemSerializer,
    StockMovementCreateSerializer,
    StockMovementSerializer,
)


class InventoryItemViewSet(RestaurantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [IsStaff]
    filterset_fields = ["is_active", "unit"]
    search_fields = ["name", "sku"]
    ordering_fields = ["name", "current_stock", "reorder_level", "updated_at"]

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        qs = self.get_queryset().filter(
            is_active=True,
            current_stock__lte=F("reorder_level"),
        ).order_by("name")
        data = InventoryItemSerializer(qs, many=True).data
        return Response(data)


class StockMovementViewSet(
    RestaurantScopedQuerysetMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = StockMovement.objects.select_related("item", "created_by").all()
    permission_classes = [IsStaff]
    filterset_fields = ["movement_type", "item"]
    search_fields = ["item__name", "item__sku", "reason", "note"]
    ordering_fields = ["created_at", "quantity"]
    restaurant_lookup = "item__restaurant"

    def get_serializer_class(self):
        if self.action == "create":
            return StockMovementCreateSerializer
        return StockMovementSerializer

    def create(self, request, *args, **kwargs):
        serializer = StockMovementCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        movement = serializer.save()

        out = StockMovementSerializer(movement, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)
