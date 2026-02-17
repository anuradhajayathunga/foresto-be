from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.mixins import RestaurantScopedQuerysetMixin
from .models import Sale
from .permissions import IsStaff
from .serializers import SaleCreateSerializer, SaleSerializer


class SaleViewSet(RestaurantScopedQuerysetMixin, viewsets.ModelViewSet):
    queryset = Sale.objects.prefetch_related("items").select_related("created_by").all()
    permission_classes = [IsStaff]
    filterset_fields = ["status", "payment_method"]
    search_fields = ["id", "customer_name", "created_by__email", "created_by__username"]
    ordering_fields = ["created_at", "total"]

    def get_serializer_class(self):
        if self.action == "create":
            return SaleCreateSerializer
        return SaleSerializer

    def create(self, request, *args, **kwargs):
        serializer = SaleCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        sale = serializer.save()

        out = SaleSerializer(sale, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def daily_summary(self, request):
        # /api/sales/sales/daily_summary/?date=2026-02-15
        d = parse_date(request.query_params.get("date", "") or "")
        qs = self.get_queryset()
        if d:
            qs = qs.filter(created_at__date=d)

        agg = qs.aggregate(count=Count("id"), total=Sum("total"))
        return Response(
            {
                "date": str(d) if d else None,
                "count": int(agg["count"] or 0),
                "total": str(agg["total"] or 0),
            }
        )

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """
        /api/sales/sales/summary/?days=7
        Returns daily totals for last N days (including today), PAID only.
        """
        try:
            days = int(request.query_params.get("days", "7"))
        except ValueError:
            days = 7
        days = max(1, min(days, 90))

        today = timezone.localdate()
        start = today - timedelta(days=days - 1)

        qs = self.get_queryset().filter(
            status="PAID",
            created_at__date__gte=start,
            created_at__date__lte=today,
        )

        rows = (
            qs.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("total"), count=Count("id"))
            .order_by("day")
        )

        by_day = {str(r["day"]): r for r in rows}
        data = []
        for i in range(days):
            d = start + timedelta(days=i)
            key = str(d)
            r = by_day.get(key)
            data.append(
                {
                    "date": key,
                    "count": int(r["count"]) if r else 0,
                    "total": str(r["total"] or 0) if r else "0",
                }
            )

        return Response(data)

    @action(detail=False, methods=["get"])
    def daily_totals(self, request):
        """
        GET /api/sales/sales/daily_totals/?days=14
        Returns daily total revenue + count for PAID sales.
        """
        try:
            days = int(request.query_params.get("days", "14"))
        except ValueError:
            days = 14
        days = max(1, min(days, 365))

        today = timezone.localdate()
        start = today - timedelta(days=days - 1)

        qs = self.get_queryset().filter(
            status="PAID",
            created_at__date__gte=start,
            created_at__date__lte=today,
        )

        rows = (
            qs.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(total=Sum("total"), count=Count("id"))
            .order_by("day")
        )

        by_day = {str(r["day"]): r for r in rows}
        data = []
        for i in range(days):
            d = start + timedelta(days=i)
            key = str(d)
            r = by_day.get(key)
            data.append(
                {
                    "date": key,
                    "count": int(r["count"]) if r else 0,
                    "total": float(r["total"] or 0) if r else 0.0,
                }
            )
        return Response(data)
