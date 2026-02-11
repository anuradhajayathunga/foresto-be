from django.db.models import F
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.tenancy import READ_ROLES, WRITE_ROLES, assert_restaurant_access
from .models import InventoryItem, StockMovement
from .serializers import (
    InventoryItemSerializer,
    StockMovementCreateSerializer,
    StockMovementSerializer,
)


class InventoryItemViewSet(viewsets.ModelViewSet):
    serializer_class = InventoryItemSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["is_active", "unit"]
    search_fields = ["name", "sku"]
    ordering_fields = ["name", "current_stock", "reorder_level", "updated_at"]

    def get_queryset(self):
        restaurant_id, _ = assert_restaurant_access(self.request, allowed_roles=READ_ROLES)
        return InventoryItem.objects.filter(restaurant_id=restaurant_id)

    def perform_create(self, serializer):
        restaurant_id, _ = assert_restaurant_access(self.request, allowed_roles=WRITE_ROLES)
        serializer.save(restaurant_id=restaurant_id)

    def perform_update(self, serializer):
        assert_restaurant_access(self.request, allowed_roles=WRITE_ROLES)
        serializer.save()

    def perform_destroy(self, instance):
        assert_restaurant_access(self.request, allowed_roles=WRITE_ROLES)
        instance.delete()

    @action(detail=False, methods=["get"])
    def low_stock(self, request):
        qs = (
            self.get_queryset()
            .filter(is_active=True, current_stock__lte=F("reorder_level"))
            .order_by("name")
        )
        data = InventoryItemSerializer(qs, many=True).data
        return Response(data)


class StockMovementViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    filterset_fields = ["movement_type", "item"]
    search_fields = ["item__name", "item__sku", "reason", "note"]
    ordering_fields = ["created_at", "quantity"]

    def get_queryset(self):
        restaurant_id, _ = assert_restaurant_access(self.request, allowed_roles=READ_ROLES)
        return StockMovement.objects.select_related("item", "created_by").filter(
            item__restaurant_id=restaurant_id
        )

    def get_serializer_class(self):
        if self.action == "create":
            return StockMovementCreateSerializer
        return StockMovementSerializer

    def create(self, request, *args, **kwargs):
        restaurant_id, _ = assert_restaurant_access(request, allowed_roles=WRITE_ROLES)

        serializer = StockMovementCreateSerializer(
            data=request.data,
            context={"request": request, "restaurant_id": restaurant_id},
        )
        serializer.is_valid(raise_exception=True)
        movement = serializer.save()

        out = StockMovementSerializer(movement, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)
