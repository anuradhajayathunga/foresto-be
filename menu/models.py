from django.db import models
from decimal import Decimal

class Category(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    sort_order = models.PositiveIntegerField(default=0)
    restaurant = models.ForeignKey(
        "accounts.Restaurant",
        on_delete=models.CASCADE,
        related_name="category",
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [models.Index(fields=["restaurant", "slug"])]
    def __str__(self):
        return self.name


class MenuItem(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="items")
    name = models.CharField(max_length=180)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_available = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    restaurant = models.ForeignKey(
        "accounts.Restaurant",
        on_delete=models.CASCADE,
        related_name="menuitem",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("category", "slug")
        ordering = ["sort_order", "name"]
        indexes = [models.Index(fields=["restaurant", "category", "slug"])]
    def __str__(self):
        return f"{self.name} ({self.category.name})"




class RecipeLine(models.Model):
    menu_item = models.ForeignKey(
        "menu.MenuItem", on_delete=models.CASCADE, related_name="recipe_lines"
    )
    ingredient = models.ForeignKey(
        "inventory.InventoryItem", on_delete=models.PROTECT, related_name="used_in_recipes"
    )
    qty = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))  # per 1 menu item
    class Meta:
        unique_together = ("menu_item", "ingredient")
        ordering = ["id"]
        indexes = [models.Index(fields=[ "menu_item", "ingredient"])] 

    def __str__(self):
        return f"{self.menu_item.name} -> {self.ingredient.name} ({self.qty})"
