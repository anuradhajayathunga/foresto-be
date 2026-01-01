from django.contrib import admin
from .models import Supplier, PurchaseInvoice, PurchaseLine

class PurchaseLineInline(admin.TabularInline):
    model = PurchaseLine
    extra = 0
    readonly_fields = ("line_total",)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "email", "phone", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "email", "phone")

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice_date", "supplier", "status", "total", "created_by")
    list_filter = ("status", "invoice_date")
    search_fields = ("id", "invoice_no", "supplier__name")
    inlines = [PurchaseLineInline]

@admin.register(PurchaseLine)
class PurchaseLineAdmin(admin.ModelAdmin):
    list_display = ("id", "invoice", "item", "qty", "unit_cost", "line_total")
