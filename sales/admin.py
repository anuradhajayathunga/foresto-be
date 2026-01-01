from django.contrib import admin
from .models import Sale, SaleItem

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    readonly_fields = ("line_total",)

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "created_by", "payment_method", "status", "total")
    list_filter = ("status", "payment_method", "created_at")
    search_fields = ("id", "customer_name", "created_by__email", "created_by__username")
    inlines = [SaleItemInline]

@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = ("id", "sale", "name", "qty", "unit_price", "line_total")
    list_filter = ("sale",)
