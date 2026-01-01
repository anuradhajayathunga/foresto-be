from django.contrib import admin
from .models import InventoryItem, StockMovement

class StockMovementInline(admin.TabularInline):
    model = StockMovement
    extra = 0
    readonly_fields = ("created_by", "created_at")

@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "sku", "unit", "current_stock", "reorder_level", "is_active")
    list_filter = ("is_active", "unit")
    search_fields = ("name", "sku")
    inlines = [StockMovementInline]

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "item", "movement_type", "quantity", "created_by", "reason")
    list_filter = ("movement_type", "created_at")
    search_fields = ("item__name", "item__sku", "reason", "note")
