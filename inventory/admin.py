from django.contrib import admin, messages
from django.utils import timezone

from .models import (
    Store, Supplier, Ingredient, MenuItem, RecipeComponent,
    InventoryRecord, Sale, PurchaseOrder, PurchaseOrderItem,
    Forecast, MessageLog
)

from inventory.services.purchase_order import generate_batch_smart_pos


# ==================================================
# STORE ACTION — AUTO PO
# ==================================================
@admin.action(description="Generate Smart Auto Purchase Orders")
def generate_auto_po(modeladmin, request, queryset):
    created_count = 0

    for store in queryset:
        pos = generate_batch_smart_pos(store=store)
        created_count += len(pos)

    if created_count == 0:
        messages.warning(request, "No purchase orders were generated.")
    else:
        messages.success(request, f"{created_count} PO(s) generated.")


# ==================================================
# PO STATUS ACTIONS  ✅ MOVE THESE UP
# ==================================================
@admin.action(description="Mark selected POs as SENT")
def mark_po_sent(modeladmin, request, queryset):
    updated = queryset.update(status="SENT")

    for po in queryset:
        MessageLog.objects.create(
            purchase_order=po,
            supplier=po.supplier,
            channel="SYSTEM",
            recipient=po.supplier.email or po.supplier.phone or "N/A",
            message_body=f"PO#{po.id} marked as SENT",
            delivery_status="SENT",
        )

    messages.success(request, f"{updated} PO(s) marked as SENT.")


@admin.action(description="Mark selected POs as CONFIRMED")
def mark_po_confirmed(modeladmin, request, queryset):
    updated = queryset.update(status="CONFIRMED")

    for po in queryset:
        MessageLog.objects.create(
            purchase_order=po,
            supplier=po.supplier,
            channel="SYSTEM",
            recipient=po.supplier.email or po.supplier.phone or "N/A",
            message_body=f"PO#{po.id} confirmed by supplier",
            delivery_status="CONFIRMED",
        )

    messages.success(request, f"{updated} PO(s) confirmed.")

@admin.action(description="Mark selected POs as RECEIVED")
def mark_po_received(modeladmin, request, queryset):
    received_count = 0

    for po in queryset:
        if po.status != "CONFIRMED":
            continue  # safety check

        for item in po.items.all():
            inventory, _ = InventoryRecord.objects.get_or_create(
                store=po.store,
                ingredient=item.ingredient,
                defaults={"quantity_on_hand": 0},
            )

            inventory.quantity_on_hand += item.ordered_quantity
            inventory.save()

        po.status = "RECEIVED"
        po.save()

        MessageLog.objects.create(
            purchase_order=po,
            supplier=po.supplier,
            channel="SYSTEM",
            recipient=po.supplier.email or po.supplier.phone or "N/A",
            message_body=f"PO#{po.id} received. Inventory updated.",
            delivery_status="RECEIVED",
        )

        received_count += 1

    if received_count == 0:
        messages.warning(request, "No confirmed POs were received.")
    else:
        messages.success(
            request,
            f"{received_count} PO(s) marked as RECEIVED and inventory updated."
        )

# ==================================================
# STORE ADMIN
# ==================================================
@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = ("name",)
    actions = [generate_auto_po]


# ==================================================
# PURCHASE ORDER ADMIN
# ==================================================
class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "store", "supplier", "status", "created_at")
    list_filter = ("status", "supplier")
    inlines = [PurchaseOrderItemInline]
    actions = [mark_po_sent, mark_po_confirmed, mark_po_received]


# ==================================================
# OTHER MODELS
# ==================================================
admin.site.register(Supplier)
admin.site.register(Ingredient)
admin.site.register(MenuItem)
admin.site.register(RecipeComponent)
admin.site.register(InventoryRecord)
admin.site.register(Sale)
admin.site.register(PurchaseOrderItem)
admin.site.register(Forecast)
admin.site.register(MessageLog)

