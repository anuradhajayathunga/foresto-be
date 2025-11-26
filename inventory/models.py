from django.db import models
from django.conf import settings

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Store(TimeStampedModel):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

    owner_id = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="store",
        help_text="Account that owns/manages this store",
    )

    def __str__(self) -> str:
        return self.name


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=200,blank=True)
    phone = models.CharField(max_length=50, blank=True)
    whatsapp_number = models.CharField(max_length=50,blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name
    

class Ingredient(TimeStampedModel):
    sku = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    unit_of_measure = models.CharField(
        max_length=20,
        help_text="kg, g, l, ml, pcs"
    )
    description = models.TextField(blank=True)

    min_stock_level = models.FloatField(null=True, blank=True)
    target_stock_level = models.FloatField(null=True, blank=True)

    default_supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_ingredients",
    )


    def __str__(self) -> str:
        return f"{self.name} - ({self.sku})"
    

class MenuItem(TimeStampedModel):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    category = models.CharField(
        max_length=100,
        blank=True,
        help_text="Rice, Noodles, Drinks",
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)


    def __str__(self) -> str:
        return f"{self.name} - {self.code}"
    

class Inventory(TimeStampedModel):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    quantity_on_hand = models.FloatField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["store", "ingredient"],
                name="unique_inventory_store_ingredient",
            )
        ]

    def __str__(self) -> str:
        return f"{self.store.name} - {self.ingredient.name}: {self.quantity_on_hand}"

class RecipeComponent(TimeStampedModel):
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="recipe_components",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="recipe_components",
    )
    quantity_per_portion = models.FloatField(
        help_text="Quantity of ingredient per one portion of menu item"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["menu_item", "ingredient"],
                name="unique_recipe_menuitem_ingredient",
            )
        ]

    

class Sale(TimeStampedModel):
    DATA_SOURCE_CHOICES = [
        ("MANUAL", "Manual entry"),
        ("POS_IMPORT", "POS import"),
    ]

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="sales",
    )
    menu_item = models.ForeignKey(
        MenuItem,
        on_delete=models.CASCADE,
        related_name="sales",
    )
    sale_date = models.DateField()
    quantity_sold = models.PositiveIntegerField()
    source = models.CharField(
        max_length=20,
        choices=DATA_SOURCE_CHOICES,
        default="MANUAL",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["store", "menu_item", "sale_date"],
                name="unique_sale_per_day",
            )
        ]

    def __str__(self) -> str:
        return f"{self.sale_date} - {self.store.name} - {self.menu_item.name}: {self.quantity_sold}"


class PurchaseOrder(TimeStampedModel):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("SENT", "Sent"),
        ("CONFIRMED", "Confirmed"),
        ("RECEIVED", "Received"),
        ("CANCELLED", "Cancelled"),
    ]

    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="purchase_orders",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.CASCADE,
        related_name="purchase_orders",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_purchase_orders",
    )

    expected_delivery_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")
    notes = models.TextField(blank=True)

    def __str__(self) -> str:
        return f"PO#{self.id} - {self.store.name} → {self.supplier.name}"
    

class PurchaseOrderItem(TimeStampedModel):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.PROTECT,
        related_name="purchase_order_items",
    )
    ordered_quantity = models.FloatField()
    unit_price = models.FloatField(null=True, blank=True)


    def __str__(self) -> str:
        return f"{self.ordered_quantity} {self.ingredient.unit_of_measure} {self.ingredient.name} in PO#{self.purchase_order.id}"
    

class Forecast(TimeStampedModel):
    store = models.ForeignKey(
        Store,
        on_delete=models.CASCADE,
        related_name="forecasts",
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name="forecasts",
    )
    forecast_date = models.DateField()
    forecast_quantity = models.FloatField()
    model_name = models.CharField(max_length=100)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["store", "ingredient", "forecast_date"],
                name="unique_forecast_per_day",
            )
        ]

    def __str__(self) -> str:
        return f"{self.forecast_date} - {self.store.name} - {self.ingredient.name}: {self.forecast_quantity}"


class MessageLog(TimeStampedModel):
    CHANNEL_CHOICES = [
        ("SMS", "SMS"),
        ("WHATSAPP", "WhatsApp"),
        ("EMAIL", "Email"),
    ]

    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
    )
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
    )

    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    recipient = models.CharField(
        max_length=100,
        help_text="Phone/WhatsApp number or email address",
    )
    message_body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    delivery_status = models.CharField(
        max_length=50,
        blank=True,
        help_text="SENT, DELIVERED, FAILED, etc.",
    )
    provider_message_id = models.CharField(max_length=100, blank=True)

    def __str__(self) -> str:
        return f"{self.channel} to {self.recipient} at {self.sent_at}"