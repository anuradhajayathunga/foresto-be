import csv
from io import TextIOWrapper
from decimal import Decimal
from django.db import transaction
from django.utils.text import slugify

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated

from inventory.permissions import IsStaff
from menu.models import Category, MenuItem, RecipeLine
from inventory.models import InventoryItem
from django.http import HttpResponse

from django.utils.dateparse import parse_datetime, parse_date
from django.utils import timezone
from sales.models import Sale, SaleItem


def to_bool(v, default=True):
    if v is None:
        return default
    s = str(v).strip().lower()
    if s in ("1", "true", "yes", "y", "on"):
        return True
    if s in ("0", "false", "no", "n", "off"):
        return False
    return default


def to_decimal(v, default="0.00"):
    if v is None or str(v).strip() == "":
        return Decimal(default)
    return Decimal(str(v).strip())


class ImportCSVView(APIView):
    """
    POST /api/import/csv/
    form-data:
      kind = categories | menu_items | ingredients | recipes
      file = <csv file>
      dry_run = true/false (optional)
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated, IsStaff]

    @transaction.atomic
    def post(self, request):
        kind = (request.data.get("kind") or "").strip()
        dry_run = to_bool(request.data.get("dry_run"), default=False)

        f = request.FILES.get("file")
        if not f:
            return Response({"detail": "CSV file is required (field name: file)."}, status=400)

        # Safe CSV reader (handles utf-8 with BOM)
        text = TextIOWrapper(f.file, encoding="utf-8-sig", newline="")
        reader = csv.DictReader(text)

        if not reader.fieldnames:
            return Response({"detail": "CSV has no header row."}, status=400)

        try:
            if kind == "categories":
                result = self.import_categories(reader)
            elif kind == "menu_items":
                result = self.import_menu_items(reader)
            elif kind == "ingredients":
                result = self.import_ingredients(reader)
            elif kind == "recipes":
                result = self.import_recipes(reader)
            elif kind == "sales":
                result = self.import_sales(reader, request)
            else:
                return Response({"detail": "Invalid kind. Use: categories | menu_items | ingredients | recipes"}, status=400)

            result["kind"] = kind
            result["dry_run"] = dry_run

            if dry_run:
                # Rollback everything
                transaction.set_rollback(True)

            return Response(result)

        except Exception as e:
            return Response({"detail": str(e)}, status=400)

    def import_categories(self, reader):
        """
        columns:
          name (required)
          slug (optional)
          sort_order (optional)
          is_active (optional)
        """
        created = 0
        updated = 0
        errors = []

        for idx, row in enumerate(reader, start=2):
            try:
                name = (row.get("name") or "").strip()
                if not name:
                    raise ValueError("name is required")

                slug = (row.get("slug") or "").strip() or slugify(name)
                sort_order = int((row.get("sort_order") or "0").strip() or "0")
                is_active = to_bool(row.get("is_active"), default=True)

                obj, was_created = Category.objects.update_or_create(
                    slug=slug,
                    defaults={"name": name, "sort_order": sort_order, "is_active": is_active},
                )
                created += 1 if was_created else 0
                updated += 0 if was_created else 1

            except Exception as e:
                errors.append({"row": idx, "error": str(e), "data": row})

        return {"created": created, "updated": updated, "errors": errors}

    def import_menu_items(self, reader):
        """
        columns:
        name (required)
        category_slug OR category_name (required)
        slug (optional -> auto from name)
        description (optional)
        price (required)
        is_available (optional)
        sort_order (optional)
        """
        created = 0
        updated = 0
        errors = []

        for idx, row in enumerate(reader, start=2):
            try:
                name = (row.get("name") or "").strip()
                if not name:
                    raise ValueError("name is required")

                cat_slug = (row.get("category_slug") or "").strip()
                cat_name = (row.get("category_name") or "").strip()
                if not cat_slug and not cat_name:
                    raise ValueError("category_slug or category_name is required")

                if cat_slug:
                    category = Category.objects.get(slug=cat_slug)
                else:
                    category = Category.objects.get(name=cat_name)

                # slug: optional -> auto-generate
                slug = (row.get("slug") or "").strip() or slugify(name)

                description = (row.get("description") or "").strip()
                price = to_decimal(row.get("price"))
                is_available = to_bool(row.get("is_available"), default=True)
                sort_order = int((row.get("sort_order") or "0").strip() or "0")

                obj, was_created = MenuItem.objects.update_or_create(
                    category=category,
                    slug=slug,  # ✅ unique with category
                    defaults={
                        "name": name,
                        "description": description,
                        "price": price,
                        "is_available": is_available,
                        "sort_order": sort_order,
                    },
                )

                created += 1 if was_created else 0
                updated += 0 if was_created else 1

            except Exception as e:
                errors.append({"row": idx, "error": str(e), "data": row})

        return {"created": created, "updated": updated, "errors": errors}

    def import_ingredients(self, reader):
        """
        columns:
          sku (required, unique)
          name (required)
          unit (required)
          reorder_level (optional)
          cost_per_unit (optional)
          current_stock (optional)  <-- updates stock directly (NO movements)
          is_active (optional)
        """
        created = 0
        updated = 0
        errors = []

        for idx, row in enumerate(reader, start=2):
            try:
                sku = (row.get("sku") or "").strip()
                name = (row.get("name") or "").strip()
                unit = (row.get("unit") or "").strip()

                if not sku:
                    raise ValueError("sku is required")
                if not name:
                    raise ValueError("name is required")
                if not unit:
                    raise ValueError("unit is required")

                reorder_level = to_decimal(row.get("reorder_level"), default="0.00")
                cost_per_unit = to_decimal(row.get("cost_per_unit"), default="0.00")
                is_active = to_bool(row.get("is_active"), default=True)

                defaults = {
                    "name": name,
                    "unit": unit,
                    "reorder_level": reorder_level,
                    "cost_per_unit": cost_per_unit,
                    "is_active": is_active,
                }

                # Optional: set stock directly (no movements)
                if row.get("current_stock") not in (None, ""):
                    defaults["current_stock"] = to_decimal(row.get("current_stock"), default="0.00")

                obj, was_created = InventoryItem.objects.update_or_create(
                    sku=sku,
                    defaults=defaults,
                )
                created += 1 if was_created else 0
                updated += 0 if was_created else 1

            except Exception as e:
                errors.append({"row": idx, "error": str(e), "data": row})

        return {"created": created, "updated": updated, "errors": errors}

    def import_recipes(self, reader):
        """
        columns:
          menu_item_name (required)
          menu_category_slug OR menu_category_name (optional but recommended)
          ingredient_sku (required)
          qty (required)  # per 1 menu item
        """
        created = 0
        updated = 0
        errors = []

        for idx, row in enumerate(reader, start=2):
            try:
                menu_name = (row.get("menu_item_name") or "").strip()
                if not menu_name:
                    raise ValueError("menu_item_name is required")

                cat_slug = (row.get("menu_category_slug") or "").strip()
                cat_name = (row.get("menu_category_name") or "").strip()

                ingredient_sku = (row.get("ingredient_sku") or "").strip()
                if not ingredient_sku:
                    raise ValueError("ingredient_sku is required")

                qty = to_decimal(row.get("qty"))
                if qty <= 0:
                    raise ValueError("qty must be > 0")

                ingredient = InventoryItem.objects.get(sku=ingredient_sku)

                # Find menu item (category filter helps if same names exist)
                if cat_slug:
                    category = Category.objects.get(slug=cat_slug)
                    menu_item = MenuItem.objects.get(category=category, name=menu_name)
                elif cat_name:
                    category = Category.objects.get(name=cat_name)
                    menu_item = MenuItem.objects.get(category=category, name=menu_name)
                else:
                    # fallback: if name is unique across menu
                    menu_item = MenuItem.objects.get(name=menu_name)

                obj, was_created = RecipeLine.objects.update_or_create(
                    menu_item=menu_item,
                    ingredient=ingredient,
                    defaults={"qty": qty},
                )
                created += 1 if was_created else 0
                updated += 0 if was_created else 1

            except Exception as e:
                errors.append({"row": idx, "error": str(e), "data": row})

        return {"created": created, "updated": updated, "errors": errors}

    def import_sales(self, reader, request):
        """
        One CSV row = one sale line
        Rows grouped by sale_ref become one Sale

        IMPORTANT:
        - During import we do NOT deduct ingredients (safe)
        - status VOID/DRAFT are allowed and do not affect stock
        """

        created = 0
        updated = 0
        errors = []

        grouped = {}
        for idx, row in enumerate(reader, start=2):
            try:
                sale_ref = (row.get("sale_ref") or "").strip()
                if not sale_ref:
                    raise ValueError("sale_ref is required")
                grouped.setdefault(sale_ref, []).append((idx, row))
            except Exception as e:
                errors.append({"row": idx, "error": str(e), "data": row})

        if errors:
            return {"created": 0, "updated": 0, "errors": errors}

        # allowed values from your model choices (optional, but helps)
        allowed_status = {c[0] for c in (Sale._meta.get_field("status").choices or [])}
        allowed_pm = {c[0] for c in (Sale._meta.get_field("payment_method").choices or [])}

        def parse_sold_at(v):
            s = (v or "").strip()
            if not s:
                return timezone.now()
            dt = parse_datetime(s)
            if dt:
                return dt if timezone.is_aware(dt) else timezone.make_aware(dt)
            d = parse_date(s)
            if d:
                dt2 = timezone.datetime(d.year, d.month, d.day, 0, 0, 0)
                return timezone.make_aware(dt2)
            raise ValueError("Invalid sold_at (use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)")

        # ✅ Always false for imports (so NO recipe deduction triggers)
        APPLY_INGREDIENTS = False

        for sale_ref, rows in grouped.items():
            try:
                first = rows[0][1]

                payment_method = (first.get("payment_method") or "").strip()
                if not payment_method:
                    raise ValueError("payment_method is required")
                if allowed_pm and payment_method not in allowed_pm:
                    raise ValueError(f"Invalid payment_method '{payment_method}'")

                status_val = (first.get("status") or "PAID").strip()
                if allowed_status and status_val not in allowed_status:
                    raise ValueError(f"Invalid status '{status_val}'")

                sold_at = parse_sold_at(first.get("sold_at"))
                customer_name = (first.get("customer_name") or "").strip()
                notes = (first.get("notes") or "").strip()
                discount = to_decimal(first.get("discount"), default="0.00")
                tax = to_decimal(first.get("tax"), default="0.00")

                # idempotent: same sale_ref updates instead of duplicates
                sale, was_created = Sale.objects.update_or_create(
                    import_ref=sale_ref,
                    defaults={
                        "sold_at": sold_at,
                        "payment_method": payment_method,
                        "status": status_val,
                        "customer_name": customer_name,
                        "notes": notes,
                        "discount": discount,
                        "tax": tax,
                        "created_by": request.user,
                    },
                )

                if not was_created:
                    SaleItem.objects.filter(sale=sale).delete()

                subtotal = Decimal("0.00")

                for sort_order, (row_idx, row) in enumerate(rows):
                    qty = int(row.get("qty") or 0)
                    if qty <= 0:
                        raise ValueError(f"Row {row_idx}: qty must be > 0")

                    menu_item = None
                    name = ""

                    menu_item_id = (row.get("menu_item_id") or "").strip()
                    cat_slug = (row.get("category_slug") or "").strip()
                    mi_slug = (row.get("menu_item_slug") or "").strip()
                    item_name = (row.get("item_name") or "").strip()

                    if menu_item_id:
                        menu_item = MenuItem.objects.get(pk=int(menu_item_id))
                    elif cat_slug and mi_slug:
                        category = Category.objects.get(slug=cat_slug)
                        menu_item = MenuItem.objects.get(category=category, slug=mi_slug)
                    elif item_name:
                        name = item_name
                    else:
                        raise ValueError(
                            f"Row {row_idx}: provide menu_item_id OR (category_slug + menu_item_slug) OR item_name"
                        )

                    unit_price = to_decimal(row.get("unit_price"), default=str(menu_item.price if menu_item else "0.00"))
                    if not name:
                        name = menu_item.name if menu_item else item_name

                    line_total = (Decimal(qty) * Decimal(unit_price)).quantize(Decimal("0.01"))
                    subtotal += line_total

                    SaleItem.objects.create(
                        sale=sale,
                        menu_item=menu_item,
                        name=name,
                        qty=qty,
                        unit_price=unit_price,
                        line_total=line_total,
                        sort_order=sort_order,
                    )

                total = (subtotal - discount + tax).quantize(Decimal("0.01"))
                if total < 0:
                    total = Decimal("0.00")

                sale.subtotal = subtotal.quantize(Decimal("0.01"))
                sale.total = total

                # ✅ Never deduct ingredients during import
                if APPLY_INGREDIENTS and sale.status == "PAID":
                    # deduct_inventory_for_sale(sale)
                    pass

                # Also mark it as NOT deducted (safe)
                sale.inventory_deducted = False
                sale.save()

                created += 1 if was_created else 0
                updated += 0 if was_created else 1

            except Exception as e:
                errors.append({"row": rows[0][0], "error": f"{sale_ref}: {e}", "data": rows[0][1]})

        return {"created": created, "updated": updated, "errors": errors}


    
    


class DownloadCSVTemplateView(APIView):
    """
    GET /api/import/template/?kind=categories
    """
    permission_classes = [IsAuthenticated, IsStaff]

    def get(self, request):
        kind = request.query_params.get("kind")
        
        # Define headers matching your ImportCSVView logic exactly
        headers_map = {
            "categories": [
                "name", "slug", "sort_order", "is_active"
            ],
            "menu_items": [
                "name", "category_name", "category_slug", "description", 
                "price", "is_available", "sort_order"
            ],
            "ingredients": [
                "sku", "name", "unit", "reorder_level", 
                "cost_per_unit", "current_stock", "is_active"
            ],
            "recipes": [
                "menu_item_name", "menu_category_name", "ingredient_sku", "qty"
            ],
            "sales": [
                        "sale_ref",
                        "sold_at",
                        "status",
                        "payment_method",
                        "customer_name",
                        "discount",
                        "tax",
                        "notes",
                        "category_slug",
                        "menu_item_slug",
                        "menu_item_id",
                        "item_name",
                        "qty",
                        "unit_price",
            ],
        }

        if kind not in headers_map:
            return HttpResponse("Invalid kind", status=400)

        # Create the response as a CSV file attachment
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="template_{kind}.csv"'

        writer = csv.writer(response)
        
        # Write the headers
        writer.writerow(headers_map[kind])
        
        # Optional: Add a sample row to help the user understand
        # (You can remove this block if you want purely empty templates)
        if kind == "categories":
            writer.writerow(["Starters", "starters", "1", "true"])
        elif kind == "menu_items":
            writer.writerow(["Chicken Soup", "Starters", "", "Delicious soup", "5.00", "true", "1"])
        elif kind == "ingredients":
            writer.writerow(["FLOUR-001", "Wheat Flour", "kg", "10", "1.50", "100", "true"])
        elif kind == "recipes":
            writer.writerow(["Chicken Soup", "Starters", "FLOUR-001", "0.2"])

        return response