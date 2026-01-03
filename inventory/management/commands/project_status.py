from django.core.management.base import BaseCommand
from inventory.models import Supplier, Store, Ingredient, PurchaseOrder
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = "Check current project status for PP-1"

    def handle(self, *args, **kwargs):
        User = get_user_model()

        self.stdout.write("\nPROJECT STATUS REPORT")
        self.stdout.write("=" * 35)

        self.stdout.write(f"Users: {User.objects.count()}")
        self.stdout.write(f"Stores: {Store.objects.count()}")
        self.stdout.write(f"Suppliers: {Supplier.objects.count()}")
        self.stdout.write(f"Ingredients: {Ingredient.objects.count()}")
        self.stdout.write(f"Purchase Orders: {PurchaseOrder.objects.count()}")

        self.stdout.write("\nCore features:")
        self.stdout.write("- Inventory management")
        self.stdout.write("- Demand forecasting (prototype)")
        self.stdout.write("- Smart PO generation")
        self.stdout.write("- Celery background tasks")

        self.stdout.write("\nRemaining work:")
        self.stdout.write("- Frontend UI")
        self.stdout.write("- Forecast optimization")
        self.stdout.write("- Validation & testing")

        self.stdout.write("\nPP-1 COMPLETION ESTIMATE: ~55%")
