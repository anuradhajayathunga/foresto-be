from django.contrib import admin
from .models import MenuItem, Category, RecipeLine

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "slug", "sort_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("sort_order", "name")


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "category", "price", "is_available", "sort_order")
    list_filter = ("category", "is_available")
    search_fields = ("name", "slug", "category__name")
    prepopulated_fields = {"slug": ("name",)}
    ordering = ("category", "sort_order", "name")



class RecipeLineInline(admin.TabularInline):
    model = RecipeLine
    extra = 0

