from decimal import Decimal
from forecasting.services_ingredients import build_ingredient_plan
from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from inventory.permissions import IsStaff  # reuse your staff permission

from .models import Supplier, PurchaseInvoice, PurchaseLine
from .serializers import (
    SupplierSerializer,
    PurchaseInvoiceOutSerializer,
    PurchaseInvoiceCreateSerializer,
    PurchaseVoidSerializer,
    PurchaseDraftFromForecastSerializer,
)

import csv
from datetime import date
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework.decorators import action


from django.utils import timezone
from django.db import transaction
from rest_framework.exceptions import ValidationError
from inventory.models import InventoryItem, StockMovement

class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsStaff]
    filterset_fields = ["is_active"]
    search_fields = ["name", "email", "phone"]
    ordering_fields = ["name"]


class PurchaseInvoiceViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = PurchaseInvoice.objects.select_related("supplier", "created_by").prefetch_related("lines__item").all()
    permission_classes = [IsStaff]
    filterset_fields = ["supplier", "status", "invoice_date"]
    search_fields = ["id", "invoice_no", "supplier__name"]
    ordering_fields = ["invoice_date", "total", "id"]

    def get_serializer_class(self):
        if self.action == "create":
            return PurchaseInvoiceCreateSerializer
        return PurchaseInvoiceOutSerializer

    def create(self, request, *args, **kwargs):
        s = PurchaseInvoiceCreateSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        invoice = s.save()
        out = PurchaseInvoiceOutSerializer(invoice, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=["get"], url_path="export-csv")
    def export_csv(self, request):
        """
        GET /api/purchases/invoices/export-csv/?from=2025-01-01&to=2025-12-31&mode=invoices|lines
        """
        mode = request.query_params.get("mode", "invoices")  # invoices | lines

        d_from = parse_date(request.query_params.get("from", "") or "")
        d_to = parse_date(request.query_params.get("to", "") or "")

        if not d_to:
            d_to = date.today()
        if not d_from:
            d_from = d_to.replace(day=1)  # default: start of current month

        qs = (
            self.get_queryset()
            .filter(invoice_date__gte=d_from, invoice_date__lte=d_to)
            .exclude(status="VOID")
            .order_by("invoice_date", "id")
        )

        resp = HttpResponse(content_type="text/csv")
        filename = f"purchases_{d_from}_to_{d_to}_{mode}.csv"
        resp["Content-Disposition"] = f'attachment; filename="{filename}"'

        writer = csv.writer(resp)

        if mode == "lines":
            writer.writerow([
                "invoice_id", "invoice_date", "supplier", "invoice_no",
                "item_sku", "item_name", "qty", "unit_cost", "line_total",
                "subtotal", "discount", "tax", "total"
            ])

            for inv in qs:
                for line in inv.lines.all():
                    writer.writerow([
                        inv.id,
                        inv.invoice_date,
                        inv.supplier.name,
                        inv.invoice_no,
                        getattr(line.item, "sku", ""),
                        getattr(line.item, "name", ""),
                        str(line.qty),
                        str(line.unit_cost),
                        str(line.line_total),
                        str(inv.subtotal),
                        str(inv.discount),
                        str(inv.tax),
                        str(inv.total),
                    ])
        else:
            writer.writerow([
                "invoice_id", "invoice_date", "supplier", "invoice_no",
                "subtotal", "discount", "tax", "total", "created_at"
            ])

            for inv in qs:
                writer.writerow([
                    inv.id,
                    inv.invoice_date,
                    inv.supplier.name,
                    inv.invoice_no,
                    str(inv.subtotal),
                    str(inv.discount),
                    str(inv.tax),
                    str(inv.total),
                    inv.created_at.isoformat(),
                ])

        return resp
    

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def void(self, request, pk=None):
        invoice = self.get_object()

        if invoice.status == "VOID":
            raise ValidationError({"detail": "Invoice is already VOID."})

        # validate input
        s = PurchaseVoidSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        reason = (s.validated_data.get("reason") or "").strip()

        # lock invoice lines + items for safe stock reversal
        lines = invoice.lines.select_related("item").all()

        # First pass: check if stock would go negative
        # (prevents partial reversal)
        for line in lines:
            item = InventoryItem.objects.select_for_update().get(pk=line.item_id)
            new_stock = item.current_stock - line.qty
            if new_stock < 0:
                raise ValidationError({
                    "detail": f"Cannot void: stock would go negative for {item.name} ({item.sku}). "
                            f"Current={item.current_stock}, Need={line.qty}."
                })

        # Second pass: apply reversal + create OUT movements
        user = request.user
        for line in lines:
            item = InventoryItem.objects.select_for_update().get(pk=line.item_id)
            item.current_stock = (item.current_stock - line.qty).quantize(Decimal("0.01"))
            item.save(update_fields=["current_stock", "updated_at"])

            StockMovement.objects.create(
                item=item,
                movement_type=StockMovement.Type.OUT,
                quantity=line.qty,
                reason="Purchase void",
                note=f"Void PurchaseInvoice #{invoice.id}" + (f" — {reason}" if reason else ""),
                created_by=user,
            )

        # mark invoice void
        if invoice.status == "DRAFT":
            invoice.status = "VOID"
            invoice.voided_at = timezone.now()
            invoice.voided_by = request.user
            invoice.void_reason = reason
            invoice.save(update_fields=["status", "voided_at", "voided_by", "void_reason"])
            out = PurchaseInvoiceOutSerializer(invoice, context={"request": request})
            return Response(out.data, status=status.HTTP_200_OK)
        

    @action(detail=False, methods=["post"], url_path="from-forecast")
    @transaction.atomic
    def from_forecast(self, request):
        """
        POST /api/purchases/invoices/from-forecast/
        body: { supplier, scope=tomorrow|next7, horizon_days=7, top_n=50, include_ok=false, invoice_date?, note? }

        Creates a DRAFT invoice using suggested_purchase_qty.
        DOES NOT update stock or create StockMovement.
        """
        s = PurchaseDraftFromForecastSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        v = s.validated_data

        supplier = Supplier.objects.get(pk=v["supplier"])
        scope = v.get("scope", "next7")
        horizon = int(v.get("horizon_days", 7))
        top_n = int(v.get("top_n", 50))
        include_ok = bool(v.get("include_ok", False))
        invoice_date = v.get("invoice_date") or timezone.localdate()
        note = (v.get("note") or "").strip()

        plan = build_ingredient_plan(horizon_days=horizon, top_n_items=top_n, scope=scope)
        ingredients = plan.get("ingredients", [])

        # Build draft lines from suggestions
        draft_lines = []
        for x in ingredients:
            if (not include_ok) and x.get("status") == "OK":
                continue

            qty = Decimal(str(x.get("suggested_purchase_qty", "0") or "0")).quantize(Decimal("0.01"))
            if qty <= 0:
                continue

            item_id = x["ingredient_id"]  # InventoryItem id
            draft_lines.append((item_id, qty))

        if not draft_lines:
            raise ValidationError({"detail": "No purchase needed (suggested_purchase_qty = 0 for all items)."})

        invoice = PurchaseInvoice.objects.create(
            supplier=supplier,
            invoice_no="",                  # optional
            invoice_date=invoice_date,
            status=PurchaseInvoice.Status.DRAFT,   # ✅ draft
            discount=Decimal("0.00"),
            tax=Decimal("0.00"),
            note=note or f"Auto draft from forecast scope={scope} start={plan.get('start_date')}",
            created_by=request.user,
        )

        subtotal = Decimal("0.00")

        # load item costs (no lock needed because we are NOT changing stock)
        items_map = {i.id: i for i in InventoryItem.objects.filter(id__in=[i for i, _ in draft_lines])}

        for idx, (item_id, qty) in enumerate(draft_lines):
            item = items_map.get(item_id)
            unit_cost = (getattr(item, "cost_per_unit", Decimal("0.00")) or Decimal("0.00")).quantize(Decimal("0.01"))
            line_total = (qty * unit_cost).quantize(Decimal("0.01"))
            subtotal += line_total

            PurchaseLine.objects.create(
                invoice=invoice,
                item_id=item_id,
                qty=qty,
                unit_cost=unit_cost,
                line_total=line_total,
                sort_order=idx,
            )

        invoice.subtotal = subtotal.quantize(Decimal("0.01"))
        invoice.total = invoice.subtotal
        invoice.save(update_fields=["subtotal", "total"])

        out = PurchaseInvoiceOutSerializer(invoice, context={"request": request})
        return Response(out.data, status=status.HTTP_201_CREATED)

