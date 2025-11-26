from django.contrib import admin
from .models import (
    Store,
    Supplier,
    Ingredient,
    MenuItem,
    RecipeComponent,
    InventoryRecord,
    Sale,
    PurchaseOrder,
    PurchaseOrderItem,
    Forecast,
    MessageLog,
)

admin.site.register(Store)
admin.site.register(Supplier)
admin.site.register(Ingredient)
admin.site.register(MenuItem)
admin.site.register(RecipeComponent)
admin.site.register(InventoryRecord)
admin.site.register(Sale)
admin.site.register(PurchaseOrder)
admin.site.register(PurchaseOrderItem)
admin.site.register(Forecast)
admin.site.register(MessageLog)
